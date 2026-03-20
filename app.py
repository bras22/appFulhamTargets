import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Fulham SF – Crew Targets", page_icon="🎯", layout="wide")
st.markdown("""
<style>
    .block-container{padding-top:1.5rem!important}
    .main-header{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);padding:1.8rem 2rem;
        border-radius:12px;color:white;text-align:center;margin-bottom:1.5rem;
        border:1px solid rgba(255,255,255,0.1)}
    .main-header h1{margin:0;font-size:2rem}
    .main-header p{margin:.3rem 0 0;opacity:.8;font-size:1.1rem}
    .summary-card{background:#1e1e2e;border-radius:10px;padding:1.2rem 1.5rem;
        text-align:center;border:1px solid rgba(255,255,255,0.08);height:100%}
    .summary-card .label{color:#aaa;font-size:.85rem;margin-bottom:.3rem}
    .summary-card .value{font-size:2.2rem;font-weight:700;line-height:1}
    .crew-card{background:#1e1e2e;border-radius:10px;padding:1.2rem;text-align:center;
        border:1px solid rgba(255,255,255,0.08);margin-bottom:1rem}
    .crew-card .crew-name{font-weight:600;font-size:.95rem;margin-bottom:.5rem;color:#e0e0e0}
    .crew-card .big-pct{font-size:2rem;font-weight:800;line-height:1}
    .badge{display:inline-block;padding:.3rem .9rem;border-radius:20px;
        font-size:.75rem;font-weight:700;letter-spacing:.04em;margin-top:.4rem}
    .badge-go{background:#1a6b3a;color:#7dffb3}
    .badge-border{background:#6b5a00;color:#ffe57d}
    .badge-stay{background:#6b1a1a;color:#ff8a8a}
    .badge-nodata{background:#333;color:#aaa}
    .green{color:#4dff91}.amber{color:#ffd54f}.red{color:#ff6b6b}.grey{color:#888}.blue{color:#7ddfff}
    .prog-wrap{background:#2a2a3e;border-radius:6px;height:12px;overflow:hidden;margin:.4rem 0}
    .prog-bar{height:100%;border-radius:6px}
    .pin-box{max-width:320px;margin:4rem auto;background:#1e1e2e;border-radius:14px;
        padding:2.5rem;text-align:center;border:1px solid rgba(255,255,255,0.1)}
    .pin-box h2{color:#e0e0e0;margin-bottom:1rem}
    .pin-box p{color:#aaa;font-size:.9rem;margin-bottom:1.5rem}
    .mgmt-header{background:linear-gradient(135deg,#0f3460,#1a2e5e);padding:1.2rem 1.5rem;
        border-radius:10px;color:white;margin-bottom:1.5rem;
        border:1px solid rgba(255,255,255,0.1);
        display:flex;justify-content:space-between;align-items:center}
</style>
""", unsafe_allow_html=True)

SHEET_ID       = "1_eWq5Mx9zBfKfkqP56wqH3uLnwbv3k714t0dztzOEo4"
MANAGEMENT_PIN = "1999"

# ── URL builders ──────────────────────────────────────────────────────────────
def gviz_url(tab):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab}"
def export_url(tab):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={tab}"

# ── Helpers ───────────────────────────────────────────────────────────────────
def status_info(pct):
    if pct>=100:  return "✅ GO HOME",      "badge-go",     "green"
    elif pct>=95: return "✅ GO (95%+)",    "badge-go",     "green"
    elif pct>=85: return "⚠️ BORDERLINE",   "badge-border", "amber"
    elif pct>0:   return "❌ SAT REQUIRED", "badge-stay",   "red"
    else:         return "— NO DATA",       "badge-nodata", "grey"

def prog_bar(pct):
    cap=min(float(pct),100)
    c="#4dff91" if pct>=95 else ("#ffd54f" if pct>=85 else "#ff6b6b")
    return f'<div class="prog-wrap"><div class="prog-bar" style="width:{cap:.1f}%;background:{c};"></div></div>'

def fmt_date(iso):
    try:    return datetime.strptime(str(iso),"%Y-%m-%d").strftime("%d %b %Y")
    except: return str(iso)

def parse_date_to_iso(v):
    if v is None: return None
    s = str(v).strip()
    if not s or s.lower() == "nan": return None
    # Handle Excel date serial numbers (e.g. 46083 = 2026-03-09)
    # PushAppSheet may send the raw numeric date value if IsDate check fails.
    # Excel epoch: 1899-12-30. Range 40000-55000 covers ~2009-2036.
    try:
        serial = float(s)
        if 40000 <= serial <= 55000:
            from datetime import timedelta as _td
            return (datetime(1899, 12, 30) + _td(days=int(serial))).strftime("%Y-%m-%d")
    except: pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except: pass
    try:    return pd.to_datetime(s, dayfirst=False).strftime("%Y-%m-%d")
    except: return None

def safe_num(v, is_daily=False):
    """
    Parse a number that may arrive in several corrupted formats due to
    Google Sheets European locale CSV export:
      "128,3333"   = comma decimal (locale stores comma as decimal sep)
      "1.411,7"    = dot thousands + comma decimal
      "303.333.333.333.333" = old VBA CStr corruption (pre-NumStr fix)
    The permanent fix is setting the Google Sheets locale to United States,
    but this function handles all variants as a safety net.
    """
    if v is None: return 0.0
    s = str(v).strip()
    if not s or s.lower() in ("nan", "—", "-", ""): return 0.0
    if s.endswith("%"):
        try:    return float(s[:-1]) / 100.0
        except: return 0.0
    # Scientific notation — corrupted percentage, ignore
    if "E+" in s.upper() or "E-" in s.upper():
        return 0.0
    # Multiple dots = old VBA CStr corruption e.g. "303.333.333.333.333"
    if s.count(".") >= 2:
        digits = s.replace(".", "")
        try:
            val = float(digits) / 1e12
            if is_daily and val > 500: val /= 10.0
            return val
        except: pass
    # "1.411,7" = dot-thousands + comma-decimal (EU locale)
    if s.count(",") == 1 and s.count(".") >= 1:
        try:
            return float(s.replace(".", "").replace(",", "."))
        except: pass
    # "128,333" = comma-decimal only (EU locale, value < 1000)
    if s.count(",") == 1 and "." not in s:
        try:
            return float(s.replace(",", "."))
        except: pass
    try:    return float(s)
    except: return 0.0

def fix_weekly(ach, tgt):
    """
    Fix Wk_Achieved values that are 10× too large due to locale corruption.
    Condition: value > 5% above target AND value÷10 ≤ target.
    E.g. Mohamed Sy Tube Install: ach=960, tgt=716.7 -> 960>752.5 AND 96<=716.7 -> fix to 96
    """
    if tgt>0 and ach>tgt*1.05 and (ach/10.0)<=tgt:
        return ach/10.0
    return ach

def task_status_style(s):
    if "On Track" in s:   return "green", "🟢"
    elif "At Risk" in s:  return "amber", "🟡"
    elif "Behind"  in s:  return "red",   "🔴"
    else:                  return "grey",  "⚪"

# ── Data loading ──────────────────────────────────────────────────────────────
def _read_csv_tab(url):
    """Fetch CSV and return clean DataFrame or None."""
    try:
        df = pd.read_csv(url, dtype=str, on_bad_lines="skip")
        if df.empty: return None
        df.columns = [str(c).strip() for c in df.columns]
        df = df[df.iloc[:,0].notna()].copy()
        df = df[~df.iloc[:,0].astype(str).str.startswith("Last refreshed")].copy()
        return df if not df.empty else None
    except: return None

@st.cache_data(ttl=300)
def load_crew_data():
    df = _read_csv_tab(gviz_url("app"))
    if df is None: df = _read_csv_tab(export_url("app"))
    if df is None: return None, "Could not fetch app tab"
    if "Person" not in df.columns:
        return None, f"Person column missing. Got: {df.columns.tolist()[:6]}"

    df = df[df["Person"].astype(str).str.strip()!=""].copy()
    if "Week_Start" not in df.columns:
        return None, "Week_Start column missing"
    df["Week_Start"] = df["Week_Start"].apply(parse_date_to_iso)
    df = df[df["Week_Start"].notna()].copy()

    # Parse daily columns with is_daily=True (applies ÷10 if >500)
    for col in ["Mon","Tue","Wed","Thu","Fri","Sat"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: safe_num(v, True))

    # Parse weekly/aggregate columns with is_daily=False
    for col in ["Wk_Achieved","Wk_Target_Real","Wk_Target_Theo",
                "Pct_Real","Remaining_Units","Days_To_Deadline"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: safe_num(v, False))

    # Fix Wk_Achieved: same 10× corruption as daily but is_daily=False so safe_num
    # didn't auto-fix. Use fix_weekly() which compares against Wk_Target_Real.
    day_sum_cols = [c for c in ["Mon","Tue","Wed","Thu","Fri","Sat"] if c in df.columns]
    if day_sum_cols:
        df["Wk_Achieved"] = df[day_sum_cols].sum(axis=1)

    # Recalculate Pct_Real from clean values
    df["Pct_Real"] = df.apply(
        lambda r: r["Wk_Achieved"]/r["Wk_Target_Real"] if r["Wk_Target_Real"]>0 else 0.0, axis=1)
    df["Person"]       = df["Person"].astype(str).str.strip()
    df["Task"]         = df["Task"].astype(str).str.strip()
    df["Sat_Decision"] = df.get("Sat_Decision", pd.Series(["No data"]*len(df))).astype(str).str.strip()
    return df, None

def load_progress_data():
    """
    Never cached — fetched fresh every time.
    Tries gviz then export URLs, both with multiple case variants.
    Validates returned data is actually the progress tab (has Row_No/No, not Person/Week_Start).
    """
    def is_progress(df):
        # Progress tab: has Row_No or No column, does NOT have Person+Week_Start
        has_id  = "Row_No" in df.columns or "No" in df.columns
        has_app = "Person" in df.columns and "Week_Start" in df.columns
        return has_id and not has_app

    errors = []
    for make_url in (gviz_url, export_url):
        for tab in ("progress","Progress","PROGRESS"):
            df = _read_csv_tab(make_url(tab))
            if df is None:
                errors.append(f"{tab} ({make_url.__name__}): empty/failed")
                continue
            if is_progress(df):
                # Parse numbers
                for col in ["Total_Required","Completed","Remaining"]:
                    if col in df.columns:
                        df[col] = df[col].apply(lambda v: safe_num(v,False))
                # Recalculate Pct_Done from integers — stored value is unreliable
                if "Total_Required" in df.columns and "Completed" in df.columns:
                    df["Pct_Done"] = df.apply(
                        lambda r: r["Completed"]/r["Total_Required"]
                                  if r["Total_Required"]>0 else 0.0, axis=1)
                return df, None
            else:
                errors.append(f"{tab} ({make_url.__name__}): got wrong tab cols={df.columns.tolist()[:5]}")

    diag = "\n".join(errors)
    return None, (
        f"Could not load the progress tab.\n\n"
        f"**Fetch attempts:**\n```\n{diag}\n```\n\n"
        f"Ensure the tab is named `progress` (lowercase) in Google Sheets "
        f"and PushProgressSheet has been run."
    )

# ── Individual view ───────────────────────────────────────────────────────────
def render_individual(df_pw, person):
    active    = df_pw[df_pw["Wk_Achieved"]>0]
    total_ach = active["Wk_Achieved"].sum()
    total_tgt = active["Wk_Target_Real"].sum()
    avg_pct   = (total_ach/total_tgt*100) if total_tgt>0 else 0.0
    sat_dec   = df_pw["Sat_Decision"].iloc[0] if len(df_pw) else "No data"
    days_left = int(df_pw["Days_To_Deadline"].iloc[0]) if len(df_pw) else 0
    label,badge,ccls = status_info(avg_pct)
    st.markdown(f"## 👤 {person}")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="summary-card"><div class="label">Total Units This Week</div><div class="value {ccls}">{total_ach:.1f}</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="summary-card"><div class="label">Avg Completion</div><div class="value {ccls}">{avg_pct:.1f}%</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="summary-card"><div class="label">Saturday Decision</div><div class="value" style="font-size:.9rem;padding-top:.8rem;"><span class="badge {badge}">{label}</span></div></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="summary-card"><div class="label">Days to Deadline</div><div class="value grey">{days_left}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    dec=sat_dec.lower()
    if "saturday required" in dec:
        st.error(f"⚠️ {sat_dec}  —  {max(0,total_tgt-total_ach):.1f} units still owed")
    elif "go home" in dec:
        st.success(f"✅ {sat_dec}")
    elif dec not in ("no activity","no data"):
        st.warning(f"📋 {sat_dec}")
    st.markdown("---")
    st.subheader("📋 Task Breakdown")
    def render_task(row,expanded=True):
        pct=row["Pct_Real"]*100
        lbl,badge_t,_=status_info(pct)
        with st.expander(f"**{row['Task']}**  —  {row['Wk_Achieved']:.1f} / {row['Wk_Target_Real']:.1f} units  ({pct:.1f}%)",expanded=expanded):
            left,right=st.columns([3,1])
            with left:
                st.markdown("**Daily Achieved:**")
                daily=pd.DataFrame({"Day":["Mon","Tue","Wed","Thu","Fri","Sat"],
                                    "Achieved":[row["Mon"],row["Tue"],row["Wed"],row["Thu"],row["Fri"],row["Sat"]]})
                st.bar_chart(daily.set_index("Day"),height=200)
            with right:
                st.markdown("**Weekly:**")
                st.metric("Achieved",f"{row['Wk_Achieved']:.1f}")
                st.metric("Target (Real)",f"{row['Wk_Target_Real']:.1f}")
                st.metric("Target (Theo)",f"{row['Wk_Target_Theo']:.1f}")
                rem=row["Wk_Target_Real"]-row["Wk_Achieved"]
                if rem>0.01: st.metric("Still Owed",f"{rem:.1f}",delta=f"{pct:.1f}%",delta_color="inverse")
                else:        st.metric("Remaining","✅ Done")
                st.markdown(prog_bar(pct),unsafe_allow_html=True)
                st.markdown(f'<span class="badge {badge_t}">{lbl}</span>',unsafe_allow_html=True)
    active_t  = df_pw[df_pw["Wk_Achieved"]>0]
    passive_t = df_pw[df_pw["Wk_Achieved"]==0]
    if len(active_t):
        st.markdown("##### 🔥 Active Tasks")
        for _,row in active_t.iterrows(): render_task(row,True)
    if len(passive_t):
        st.markdown("##### 📌 No Activity This Week")
        for _,row in passive_t.iterrows(): render_task(row,False)

# ── Task View (public) ────────────────────────────────────────────────────────
def render_taskview():
    st.markdown("## 🔧 Task View — All Crew Breakdown")
    df_app,err = load_crew_data()
    if df_app is None:
        st.error(f"Could not load crew data: `{err}`"); return
    all_tasks = sorted(df_app["Task"].dropna().unique().tolist())
    all_weeks = sorted(df_app["Week_Start"].dropna().unique().tolist())
    if not all_tasks:
        st.warning("No task data. Run RefreshAppSheet → PushAll in Excel."); return
    c1,c2 = st.columns(2)
    with c1: sel_task = st.selectbox("Task",all_tasks)
    with c2: sel_week = st.selectbox("Week",all_weeks,
                         format_func=lambda w:fmt_date(w) if w else str(w),
                         index=len(all_weeks)-1 if all_weeks else 0)
    df_tv = df_app[(df_app["Task"]==sel_task)&(df_app["Week_Start"]==sel_week)].copy()
    if df_tv.empty:
        st.warning(f"No data for **{sel_task}** week `{sel_week}`."); return
    df_tv["Pct_Completion"] = df_tv.apply(
        lambda r: r["Wk_Achieved"]/r["Wk_Target_Real"]*100 if r["Wk_Target_Real"]>0 else 0.0, axis=1)
    # Task_Wk_Target = tTpd × 5.5 (added in latest VBA — push RefreshAppSheet to get it)
    # Wk_Target_Theo = per-crew target = tTpd/tPplPlan × 5.5
    has_task_tgt = "Task_Wk_Target" in df_tv.columns
    task_wk_tgt  = safe_num(df_tv["Task_Wk_Target"].iloc[0]) if has_task_tgt else 0
    active_count = len(df_tv[df_tv["Wk_Achieved"] > 0])
    # Per-person target = task total ÷ active crew (2530/3=843.3)
    # This is the only reliable basis — Wk_Target_Real/Theo from VBA are partial-week values
    if task_wk_tgt > 0 and active_count > 0:
        wk_tgt_pp = task_wk_tgt / active_count
    else:
        wk_tgt_pp = safe_num(df_tv["Wk_Target_Real"].iloc[0]) \
                    if "Wk_Target_Real" in df_tv.columns else 0
    df_tv["Pct_Completion"] = df_tv.apply(
        lambda r: r["Wk_Achieved"] / r["Wk_Target_Real"] * 100
                  if r["Wk_Target_Real"] > 0 else 0.0, axis=1)
 
    team_total   = df_tv["Wk_Achieved"].sum()
    days_left    = int(df_tv["Days_To_Deadline"].iloc[0]) if "Days_To_Deadline" in df_tv.columns else 0

    # If Task_Wk_Target not yet pushed, show per-crew metric instead of 0
    if task_wk_tgt > 0:
        team_pct = (team_total / task_wk_tgt * 100)
        tgt_label = "Weekly Target (Task)"
        tgt_val   = f"{task_wk_tgt:.0f}"
        pct_label = "Team Completion"
        pct_val   = f"{team_pct:.1f}%"
        _,_,ccls_t = status_info(team_pct)
        caption_extra = f"Weekly task target: **{task_wk_tgt:.0f}**  ·  "
    else:
        # Fallback: show per-crew target, note that RefreshAppSheet is needed
        team_pct  = 0.0
        tgt_label = "Target / Crew"
        tgt_val   = f"{wk_tgt_pp:.0f}"
        pct_label = "Active Crew"
        pct_val   = str(active_count)
        ccls_t    = "blue"
        caption_extra = "⚠️ Run **RefreshAppSheet → PushAll** to see task weekly target  ·  "

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="summary-card"><div class="label">Task</div><div class="value blue" style="font-size:1rem;padding-top:.5rem;">{sel_task}</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="summary-card"><div class="label">Team Total This Week</div><div class="value {ccls_t}">{team_total:.0f}</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="summary-card"><div class="label">{tgt_label}</div><div class="value blue">{tgt_val}</div></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="summary-card"><div class="label">{pct_label}</div><div class="value {ccls_t}">{pct_val}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    if task_wk_tgt > 0:
        st.markdown(prog_bar(team_pct),unsafe_allow_html=True)
    st.caption(f"{caption_extra}Target per crew: **{wk_tgt_pp:.0f}**  ·  Active: **{active_count}** crew  ·  Days to deadline: **{days_left}**")
    st.markdown("---")
    active_crew   = df_tv[df_tv["Wk_Achieved"]>0].sort_values("Pct_Completion",ascending=False)
    inactive_crew = df_tv[df_tv["Wk_Achieved"]==0].sort_values("Person")
    if len(active_crew):
        st.subheader(f"🔥 Active Crew ({len(active_crew)})")
        cols=st.columns(4)
        for idx,(_,row) in enumerate(active_crew.iterrows()):
            pct=row["Pct_Completion"]; lbl,badge,ccls=status_info(pct)
            with cols[idx%4]:
                st.markdown(
                    f'<div class="crew-card"><div class="crew-name">{row["Person"]}</div>'
                    f'<div class="big-pct {ccls}">{pct:.1f}%</div>{prog_bar(pct)}'
                    f'<div style="font-size:.8rem;color:#aaa;margin-top:.3rem;">{row["Wk_Achieved"]:.1f} / {row["Wk_Target_Real"]:.1f} units</div>'
                    f'<span class="badge {badge}">{lbl}</span></div>',unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("📊 Daily Breakdown")
        day_cols=[c for c in ["Person","Mon","Tue","Wed","Thu","Fri","Sat",
                               "Wk_Achieved","Wk_Target_Real","Remaining_Units","Pct_Completion"]
                  if c in active_crew.columns]
        df_d=active_crew[day_cols].copy()
        # Build sum row before formatting
        num_cols = [c for c in day_cols if c not in ("Person","Pct_Completion")]
        sum_vals = {c: df_d[c].sum() if c in num_cols else
                       ("TOTAL" if c=="Person" else "") for c in day_cols}
        s_ach = sum_vals.get("Wk_Achieved", 0)
        s_tgt = sum_vals.get("Wk_Target_Real", 0)
        sum_vals["Pct_Completion"] = (s_ach / s_tgt * 100) if s_tgt > 0 else 0.0
        df_d = pd.concat([df_d, pd.DataFrame([sum_vals])], ignore_index=True)
        for col in [c for c in day_cols if c!="Person"]:
            df_d[col]=df_d[col].apply(
                lambda x: f"{float(x):.1f}%" if col=="Pct_Completion"
                          else f"{float(x):.1f}" if str(x) not in ("","nan") else "—")
        st.dataframe(df_d.rename(columns={"Person":"Crew","Wk_Achieved":"Week Total",
            "Wk_Target_Real":"Target/Crew","Remaining_Units":"Remaining","Pct_Completion":"% Done"}),
            use_container_width=True,hide_index=True)

    if len(inactive_crew):
        with st.expander(f"👻 {len(inactive_crew)} crew with no activity this week"):
            for _,row in inactive_crew.iterrows(): st.markdown(f"- {row['Person']}")

# ── Team Overview ─────────────────────────────────────────────────────────────
def render_team(df_week,week_lbl):
    st.markdown(f"## 👥 All Crew — {week_lbl}")
    if df_week.empty: st.info("No data for this week."); return
    def person_summary(grp):
        worked=grp[grp["Wk_Achieved"]>0]
        ach=worked["Wk_Achieved"].sum(); tgt=worked["Wk_Target_Real"].sum()
        return pd.Series({"total_ach":ach,"total_tgt":tgt,
                          "pct":(ach/tgt*100) if tgt>0 else 0.0,
                          "sat_dec":grp["Sat_Decision"].iloc[0],"active":ach>0})
    summary=df_week.groupby("Person").apply(person_summary).reset_index()
    summary=pd.concat([summary[summary["active"]].sort_values("pct",ascending=False),
                       summary[~summary["active"]].sort_values("Person")],ignore_index=True)
    on_track=int((summary["pct"]>=95).sum())
    borderline=int(((summary["pct"]>=85)&(summary["pct"]<95)).sum())
    need_sat=int((summary["active"]&(summary["pct"]<85)).sum())
    no_act=int((~summary["active"]).sum())
    mc1,mc2,mc3,mc4=st.columns(4)
    mc1.metric("✅ On Track (≥95%)",on_track)
    mc2.metric("⚠️ Borderline (85–94%)",borderline)
    mc3.metric("❌ Need Saturday (<85%)",need_sat)
    mc4.metric("— No Activity",no_act)
    st.markdown("---")
    cols=st.columns(4)
    for i,row in summary.iterrows():
        pct,active=row["pct"],row["active"]
        if active:
            lbl,badge,ccls=status_info(pct)
            pct_str=f"{pct:.1f}%"; units_str=f'{row["total_ach"]:.0f} / {row["total_tgt"]:.0f} units'
        else:
            lbl,badge,ccls="— NO DATA","badge-nodata","grey"
            pct_str,units_str="—","No activity this week"
        with cols[i%4]:
            st.markdown(
                f'<div class="crew-card"><div class="crew-name">{row["Person"]}</div>'
                f'<div class="big-pct {ccls}">{pct_str}</div>'
                f'{prog_bar(pct) if active else ""}'
                f'<div style="font-size:.8rem;color:#aaa;margin-top:.3rem;">{units_str}</div>'
                f'<span class="badge {badge}">{lbl}</span></div>',unsafe_allow_html=True)

# ── Project Progress ──────────────────────────────────────────────────────────
def render_mgmt_progress():
    st.markdown("## 📊 Project Progress")
    df,err = load_progress_data()
    if df is None:
        st.warning(f"**Progress data unavailable:**\n\n{err}"); return
    id_col="Row_No" if "Row_No" in df.columns else ("No" if "No" in df.columns else None)
    if id_col:
        overall_df = df[df[id_col].astype(str).str.strip()=="0"]
        task_df    = df[df[id_col].astype(str).str.strip()!="0"].copy()
    else:
        overall_df = df[df["Task"].astype(str).str.contains("OVERALL",case=False,na=False)]
        task_df    = df[~df["Task"].astype(str).str.contains("OVERALL",case=False,na=False)].copy()
    task_df = task_df[task_df["Task"].astype(str).str.strip()!=""].copy()

    # Summary row values
    total_req=0.0; total_done=0.0; total_rem=0.0; ov_pct=0.0; deadline=""; days_left=""
    if len(overall_df):
        or_=overall_df.iloc[0]
        total_req  = safe_num(or_.get("Total_Required",0))
        total_done = safe_num(or_.get("Completed",0))
        total_rem  = safe_num(or_.get("Remaining",0))
        ov_pct     = (total_done/total_req*100) if total_req>0 else 0.0
        deadline   = str(or_.get("Deadline",""))
        days_left  = str(or_.get("Days_Left","")).replace("DAYS TO DEADLINE:","").strip()
    elif len(task_df):
        total_req  = task_df["Total_Required"].sum() if "Total_Required" in task_df.columns else 0
        total_done = task_df["Completed"].sum()      if "Completed"      in task_df.columns else 0
        total_rem  = total_req-total_done
        ov_pct     = (total_done/total_req*100)      if total_req>0 else 0.0

    clr="green" if ov_pct>=80 else ("amber" if ov_pct>=40 else "red")
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(f'<div class="summary-card"><div class="label">Total Required</div><div class="value blue">{total_req:,.0f}</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="summary-card"><div class="label">Completed</div><div class="value green">{total_done:,.0f}</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="summary-card"><div class="label">Remaining</div><div class="value amber">{total_rem:,.0f}</div></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="summary-card"><div class="label">Overall % Done</div><div class="value {clr}">{ov_pct:.1f}%</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown(prog_bar(ov_pct),unsafe_allow_html=True)
    ci1,ci2=st.columns(2)
    with ci1: st.info(f"🗓 **Deadline:** {fmt_date(parse_date_to_iso(deadline)) if deadline else '—'}")
    with ci2: st.info(f"⏳ **Days to Deadline:** {days_left if days_left else '—'}")
    st.markdown("---")

    # Per-task cards 2-column grid
    task_rows=[row for _,row in task_df.iterrows()
               if str(row.get("Task","")).strip() not in ("","nan")]
    for i in range(0,len(task_rows),2):
        cols=st.columns(2)
        for ci,row in enumerate(task_rows[i:i+2]):
            task    =str(row.get("Task",""))
            req     =float(row.get("Total_Required",0))
            done    =float(row.get("Completed",0))
            pct     =(done/req*100) if req>0 else 0.0
            rate_2wk=str(row.get("Rate_2wk","—"))
            reqd_r  =str(row.get("Reqd_Rate","—"))
            proj_fin=str(row.get("Proj_Finish","—"))
            status  =str(row.get("Status","—"))
            row_no  =str(row.get(id_col,"")) if id_col else ""
            clr2,icon=task_status_style(status)
            bar_c="#4dff91" if pct>=80 else ("#ffd54f" if pct>=50 else "#ff6b6b")
            cap=min(pct,100)
            txt_c={"green":"#4dff91","amber":"#ffd54f","red":"#ff6b6b"}.get(clr2,"#888")
            proj_fmt=fmt_date(parse_date_to_iso(proj_fin)) if proj_fin not in ("?","—","") else proj_fin
            with cols[ci]:
                st.markdown(f"""
<div style="background:#1e1e2e;border-radius:10px;padding:1.2rem;
     border:1px solid rgba(255,255,255,0.08);margin-bottom:1rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem;">
    <span style="font-weight:700;font-size:.95rem;color:#e0e0e0;">{row_no}. {task}</span>
    <span style="font-size:.8rem;font-weight:700;color:{txt_c};">{icon} {status}</span>
  </div>
  <div style="background:#2a2a3e;border-radius:6px;height:10px;overflow:hidden;margin-bottom:.7rem;">
    <div style="width:{cap:.1f}%;height:100%;background:{bar_c};border-radius:6px;"></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.3rem;font-size:.82rem;text-align:center;margin-bottom:.5rem;">
    <div><span style="color:#aaa;display:block;font-size:.75rem;">Required</span><span style="font-weight:700;color:#7ddfff;">{req:,.0f}</span></div>
    <div><span style="color:#aaa;display:block;font-size:.75rem;">Completed</span><span style="font-weight:700;color:#4dff91;">{done:,.0f}</span></div>
    <div><span style="color:#aaa;display:block;font-size:.75rem;">% Done</span><span style="font-weight:700;color:{txt_c};">{pct:.1f}%</span></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.3rem;font-size:.78rem;text-align:center;">
    <div><span style="color:#aaa;display:block;font-size:.72rem;">Rate/day</span><span style="color:#e0e0e0;">{rate_2wk}</span></div>
    <div><span style="color:#aaa;display:block;font-size:.72rem;">Req'd Rate</span><span style="color:#e0e0e0;">{reqd_r}</span></div>
    <div><span style="color:#aaa;display:block;font-size:.72rem;">Proj. Finish</span><span style="color:#e0e0e0;">{proj_fmt}</span></div>
  </div>
</div>""",unsafe_allow_html=True)

    if "Explanation" in task_df.columns:
        st.markdown("---"); st.subheader("📝 Detail per Task")
        for _,row in task_df.iterrows():
            s=str(row.get("Status",""));_,icon=task_status_style(s)
            task=str(row.get("Task",""))
            if not task or task.lower() in ("nan",""): continue
            with st.expander(f"{icon} **{task}** — {s}"):
                st.code(str(row.get("Explanation","")).replace(" | ","\n"),language=None)

# ── PIN gate ──────────────────────────────────────────────────────────────────
def render_pin_gate():
    if st.session_state.get("mgmt_auth",False): return True
    st.markdown('<div class="pin-box"><h2>🔒 Management Access</h2><p>Enter the 4-digit PIN to continue.</p></div>',unsafe_allow_html=True)
    col=st.columns([1,1,1])[1]
    with col:
        pin=st.text_input("PIN",type="password",max_chars=4,placeholder="• • • •",label_visibility="collapsed")
        if st.button("🔓 Unlock",use_container_width=True):
            if pin==MANAGEMENT_PIN:
                st.session_state["mgmt_auth"]=True; st.rerun()
            else:
                st.error("Incorrect PIN.")
    return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if "mgmt_auth" not in st.session_state: st.session_state["mgmt_auth"]=False
    df,err = load_crew_data()

    st.sidebar.title("🔍 Navigation")
    view=st.sidebar.radio("View",["👤 Individual","🔧 Task View","🔒 Management"])

    sel_week=None; sel_week_lbl=""; sel_person=None
    week_labels={}; persons=[]; latest=""

    if df is not None:
        weeks_raw   = sorted(df["Week_Start"].dropna().unique())
        week_labels = {w:f"{fmt_date(w)}  (Week {i+1})" for i,w in enumerate(weeks_raw)}

        # Default to most recent week that has ANY activity (not current empty week)
        def _last_active(df, wks):
            for w in reversed(wks):
                if df is not None and df[df["Week_Start"]==w]["Wk_Achieved"].sum() > 0:
                    return w
            return wks[-1] if wks else None
        best_week     = _last_active(df, list(weeks_raw))
        best_week_idx = list(weeks_raw).index(best_week) if best_week in list(weeks_raw) else max(0, len(weeks_raw)-1)

        week_options= list(week_labels.values())
        persons     = sorted(df["Person"].unique().tolist())
        latest      = weeks_raw[-1] if weeks_raw else ""
        if view=="👤 Individual":
            st.sidebar.markdown("**Select Week:**")
            sel_week_lbl=st.sidebar.selectbox("",week_options,index=best_week_idx,label_visibility="collapsed")
            sel_week=next((w for w,lbl in week_labels.items() if lbl==sel_week_lbl), best_week)
            st.sidebar.markdown("**Select Person:**")
            sel_person=st.sidebar.selectbox("",["— Select a crew member —"]+persons,label_visibility="collapsed")

    st.sidebar.markdown("---")
    st.sidebar.caption("**Daily workflow:**\n\n1. Import QField → Excel\n2. Run **RefreshAppSheet**\n3. Run **PushAll**\n4. Click Reload ↓")
    if df is not None:
        st.sidebar.caption(f"📊 {len(df)} rows · {len(week_labels)} weeks\n\n🕒 {datetime.now().strftime('%I:%M %p, %d %b %Y')}")
    if st.sidebar.button("🔄 Clear Cache & Reload"):
        st.cache_data.clear(); st.session_state["mgmt_auth"]=False; st.rerun()

    st.markdown(
        f'<div class="main-header"><h1>🎯 Fulham Solar Farm — Weekly Targets</h1>'
        f'<p>Latest data: {fmt_date(latest) if latest else "—"}'
        f'  ·  {len(week_labels)} week{"s" if len(week_labels)!=1 else ""} tracked'
        f'  ·  {len(persons)} crew members</p></div>',unsafe_allow_html=True)

    if view=="🔧 Task View":
        render_taskview(); return

    if view=="🔒 Management":
        if not render_pin_gate(): return
        st.markdown('<div class="mgmt-header"><span style="font-size:1.2rem;font-weight:700;">🔒 Management Dashboard</span><span style="font-size:.85rem;opacity:.7;">Restricted access</span></div>',unsafe_allow_html=True)
        mgmt_tab=st.radio("Section",["👥 Team Overview","📊 Project Progress"],horizontal=True)
        if mgmt_tab=="👥 Team Overview":
            if df is None: st.error(f"Could not load crew data: `{err}`")
            else:
                if week_labels:
                    st.sidebar.markdown("**Select Week:**")
                    mgmt_wlbl=st.sidebar.selectbox("Week (mgmt)",list(week_labels.values()),index=best_week_idx,label_visibility="collapsed")
                    mgmt_week=next((w for w,lbl in week_labels.items() if lbl==mgmt_wlbl), best_week)
                    render_team(df[df["Week_Start"]==mgmt_week].copy(),mgmt_wlbl)
        else:
            render_mgmt_progress()
        st.markdown("---")
        if st.button("🔒 Lock Management Area"):
            st.session_state["mgmt_auth"]=False; st.rerun()
        return

    if df is None:
        st.error(f"Could not load crew data.\n\n`{err}`"); return
    if sel_person is None or sel_person == "— Select a crew member —":
        st.markdown(
            '<div style="text-align:center;padding:4rem 2rem;">'
            '<div style="font-size:3rem;margin-bottom:1rem;">👷</div>'
            '<h2 style="color:#e0e0e0;margin-bottom:0.5rem;">Select your name and week</h2>'
            '<p style="color:#aaa;font-size:1rem;">Use the sidebar on the left to choose a crew member and week,'
            ' then your personal targets and progress will appear here.</p>'
            '</div>',
            unsafe_allow_html=True)
    else:
        df_pw=df[(df["Week_Start"]==sel_week)&(df["Person"]==sel_person)].copy()
        if len(df_pw)==0:
            all_w=sorted(df[df["Person"]==sel_person]["Week_Start"].unique())
            st.warning(f"No data for **{sel_person}** in week `{sel_week}`.\n\nWeeks found: `{all_w}`")
        else:
            render_individual(df_pw,sel_person)

if __name__=="__main__":
    main()
