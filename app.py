import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Fulham SF – Crew Targets", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem !important; }
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.8rem 2rem; border-radius: 12px; color: white;
        text-align: center; margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .main-header h1 { margin: 0; font-size: 2rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.8; font-size: 1.1rem; }
    .summary-card {
        background: #1e1e2e; border-radius: 10px; padding: 1.2rem 1.5rem;
        text-align: center; border: 1px solid rgba(255,255,255,0.08); height: 100%;
    }
    .summary-card .label { color: #aaa; font-size: 0.85rem; margin-bottom: 0.3rem; }
    .summary-card .value { font-size: 2.2rem; font-weight: 700; line-height: 1; }
    .crew-card {
        background: #1e1e2e; border-radius: 10px; padding: 1.2rem;
        text-align: center; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 1rem;
    }
    .crew-card .crew-name { font-weight:600; font-size:0.95rem; margin-bottom:0.5rem; color:#e0e0e0; }
    .crew-card .big-pct   { font-size:2rem; font-weight:800; line-height:1; }
    .badge {
        display:inline-block; padding:0.3rem 0.9rem; border-radius:20px;
        font-size:0.75rem; font-weight:700; letter-spacing:0.04em; margin-top:0.4rem;
    }
    .badge-go     { background:#1a6b3a; color:#7dffb3; }
    .badge-border { background:#6b5a00; color:#ffe57d; }
    .badge-stay   { background:#6b1a1a; color:#ff8a8a; }
    .badge-nodata { background:#333;    color:#aaa; }
    .badge-track  { background:#1a4b6b; color:#7ddfff; }
    .badge-risk   { background:#6b4a00; color:#ffc87d; }
    .badge-behind { background:#6b1a1a; color:#ff8a8a; }
    .green { color:#4dff91; } .amber { color:#ffd54f; }
    .red   { color:#ff6b6b; } .grey  { color:#888; }
    .blue  { color:#7ddfff; }
    .prog-wrap { background:#2a2a3e; border-radius:6px; height:12px; overflow:hidden; margin:0.4rem 0; }
    .prog-bar  { height:100%; border-radius:6px; }
    .pin-box {
        max-width: 320px; margin: 4rem auto; background: #1e1e2e;
        border-radius: 14px; padding: 2.5rem; text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .pin-box h2 { color: #e0e0e0; margin-bottom: 1rem; }
    .pin-box p  { color: #aaa; font-size: 0.9rem; margin-bottom: 1.5rem; }
    .mgmt-header {
        background: linear-gradient(135deg, #0f3460 0%, #1a2e5e 100%);
        padding: 1.2rem 1.5rem; border-radius: 10px; color: white;
        margin-bottom: 1.5rem; border: 1px solid rgba(255,255,255,0.1);
        display: flex; justify-content: space-between; align-items: center;
    }
    .tv-team-row { background: #16213e !important; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

SHEET_ID       = "1_eWq5Mx9zBfKfkqP56wqH3uLnwbv3k714t0dztzOEo4"
MANAGEMENT_PIN = "1999"

def sheet_url(tab):
    return (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            f"/export?format=csv&sheet={tab}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def status_info(pct):
    if pct >= 100:  return "✅ GO HOME",      "badge-go",     "green"
    elif pct >= 95: return "✅ GO (95%+)",    "badge-go",     "green"
    elif pct >= 85: return "⚠️ BORDERLINE",   "badge-border", "amber"
    elif pct > 0:   return "❌ SAT REQUIRED", "badge-stay",   "red"
    else:           return "— NO DATA",       "badge-nodata", "grey"

def prog_bar(pct):
    cap = min(float(pct), 100)
    c = "#4dff91" if pct >= 95 else ("#ffd54f" if pct >= 85 else "#ff6b6b")
    return (f'<div class="prog-wrap">'
            f'<div class="prog-bar" style="width:{cap:.1f}%;background:{c};"></div>'
            f'</div>')

def fmt_date(iso_str):
    try:    return datetime.strptime(str(iso_str), "%Y-%m-%d").strftime("%d %b %Y")
    except: return str(iso_str)

def parse_date_to_iso(v):
    if v is None: return None
    s = str(v).strip()
    if not s or s.lower() == "nan": return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except: pass
    try:    return pd.to_datetime(s, dayfirst=False).strftime("%Y-%m-%d")
    except: return None

def safe_num(v, is_daily=False):
    if v is None: return 0.0
    s = str(v).strip()
    if not s or s.lower() in ("nan", "—", "-", ""): return 0.0
    if s.endswith("%"):
        try:    return float(s[:-1]) / 100.0
        except: return 0.0
    if s.count(".") >= 2:
        digits = s.replace(".", "")
        try:
            val = float(digits) / 1e12
            if is_daily and val > 500: val = val / 10.0
            return val
        except: pass
    try:    return float(s)
    except: return 0.0

def progress_status(status_str):
    s = str(status_str).strip()
    if "On Track" in s:   return "badge-track",  "🟢"
    elif "At Risk" in s:  return "badge-risk",   "🟡"
    elif "Complete" in s: return "badge-go",     "✅"
    elif "Stalled" in s:  return "badge-risk",   "⚠️"
    else:                 return "badge-behind",  "🔴"

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_tab(tab_name):
    try:
        df = pd.read_csv(sheet_url(tab_name), dtype=str, on_bad_lines="skip")
    except Exception as e:
        return None, str(e)
    if df.empty:
        return None, f"Tab '{tab_name}' is empty."
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df.iloc[:, 0].notna()].copy()
    df = df[~df.iloc[:, 0].astype(str).str.startswith("Last refreshed")].copy()
    return df, None

@st.cache_data(ttl=300)
def load_crew_data():
    df, err = load_tab("app")
    if df is None: return None, err
    if "Person" not in df.columns:
        return None, f"'Person' column missing. Columns: {df.columns.tolist()[:8]}"
    df = df[df["Person"].astype(str).str.strip() != ""].copy()
    df = df[~df["Person"].astype(str).str.startswith("Last refreshed")].copy()
    if "Week_Start" not in df.columns:
        return None, "'Week_Start' column missing."
    df["Week_Start"] = df["Week_Start"].apply(parse_date_to_iso)
    df = df[df["Week_Start"].notna()].copy()
    for col in ["Mon","Tue","Wed","Thu","Fri","Sat"]:
        if col in df.columns: df[col] = df[col].apply(lambda v: safe_num(v, True))
    for col in ["Wk_Achieved","Wk_Target_Real","Wk_Target_Theo","Pct_Real","Remaining_Units","Days_To_Deadline"]:
        if col in df.columns: df[col] = df[col].apply(lambda v: safe_num(v, False))
    df["Pct_Real"] = df.apply(
        lambda r: r["Wk_Achieved"] / r["Wk_Target_Real"] if r["Wk_Target_Real"] > 0 else 0.0, axis=1)
    df["Person"]       = df["Person"].astype(str).str.strip()
    df["Task"]         = df["Task"].astype(str).str.strip()
    df["Sat_Decision"] = df.get("Sat_Decision", pd.Series(["No data"]*len(df))).astype(str).str.strip()
    return df, None

@st.cache_data(ttl=300)
def load_taskview_data():
    """
    Loads the 'taskview' tab pushed by PushTaskViewSheet.
    Guard: if Google Sheets returns the wrong tab (e.g. 'app' tab when
    'taskview' didn't exist yet), it will have 'Person' column — we detect
    that and return a helpful error instead of silently showing wrong data.
    """
    df, err = load_tab("taskview")
    if df is None: return None, err

    # Detect wrong-tab scenario: Google Sheets returns first sheet silently
    if "Person" in df.columns and "Crew_Member" not in df.columns:
        return None, (
            "taskview tab not pushed yet — Google Sheets returned the wrong tab.\n"
            "Run **PushTaskViewSheet** (or **PushAll**) from Excel, then click Reload."
        )
    if "Crew_Member" not in df.columns:
        return None, f"taskview tab not pushed yet. Columns: {df.columns.tolist()}"

    df = df[df["Crew_Member"].astype(str).str.strip() != ""].copy()

    # Parse dates
    if "Week_Start" in df.columns:
        df["Week_Start"] = df["Week_Start"].apply(parse_date_to_iso)

    # Daily columns (Mon-Sat): max ~700/day per person → is_daily=True
    for col in ["Mon","Tue","Wed","Thu","Fri","Sat"]:
        if col in df.columns: df[col] = df[col].apply(lambda v: safe_num(v, True))

    # Weekly/aggregate columns → is_daily=False
    for col in ["Day_Target","Wk_Target","Wk_Total","Wk_Target_Person","Units_Left"]:
        if col in df.columns: df[col] = df[col].apply(lambda v: safe_num(v, False))

    # Pct_Real from TASK VIEW is stored as ±fraction (can be negative = behind).
    # We recalculate from Wk_Total / Wk_Target_Person to get true completion %.
    if "Wk_Total" in df.columns and "Wk_Target_Person" in df.columns:
        df["Pct_Completion"] = df.apply(
            lambda r: (r["Wk_Total"] / r["Wk_Target_Person"] * 100)
                      if r["Wk_Target_Person"] > 0 else 0.0, axis=1)
    else:
        df["Pct_Completion"] = 0.0

    if "Is_Team_Total" in df.columns:
        df["Is_Team_Total"] = df["Is_Team_Total"].astype(str).str.strip()

    return df, None

@st.cache_data(ttl=300)
def load_progress_data():
    df, err = load_tab("progress")
    if df is None: return None, err
    if "Task" not in df.columns:
        return None, f"progress tab not pushed yet. Columns: {df.columns.tolist()}"

    # Skip the OVERALL SUMMARY row
    row_id_col = None
    if "Row_No" in df.columns: row_id_col = "Row_No"
    elif "No"    in df.columns: row_id_col = "No"

    if row_id_col:
        df = df[df[row_id_col].astype(str).str.strip() != "0"].copy()
    else:
        df = df[~df["Task"].astype(str).str.contains("OVERALL", case=False, na=False)].copy()

    # Drop truly empty task rows
    df = df[df["Task"].astype(str).str.strip() != ""].copy()

    for col in ["Total_Required","Completed","Remaining"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "Pct_Done" in df.columns:
        df["Pct_Done"] = df["Pct_Done"].apply(lambda v: safe_num(v, False))
    return df, None

def render_individual(df_pw, person):
    active    = df_pw[df_pw["Wk_Achieved"] > 0]
    total_ach = active["Wk_Achieved"].sum()
    total_tgt = active["Wk_Target_Real"].sum()
    avg_pct   = (total_ach / total_tgt * 100) if total_tgt > 0 else 0.0
    sat_dec   = df_pw["Sat_Decision"].iloc[0] if len(df_pw) else "No data"
    days_left = int(df_pw["Days_To_Deadline"].iloc[0]) if len(df_pw) else 0

    label, badge, ccls = status_info(avg_pct)
    st.markdown(f"## 👤 {person}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="summary-card"><div class="label">Total Units This Week</div>'
                    f'<div class="value {ccls}">{total_ach:.1f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="summary-card"><div class="label">Avg Completion</div>'
                    f'<div class="value {ccls}">{avg_pct:.1f}%</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="summary-card"><div class="label">Saturday Decision</div>'
                    f'<div class="value" style="font-size:0.9rem;padding-top:0.8rem;">'
                    f'<span class="badge {badge}">{label}</span></div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="summary-card"><div class="label">Days to Deadline</div>'
                    f'<div class="value grey">{days_left}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    dec = sat_dec.lower()
    if "saturday required" in dec:
        st.error(f"⚠️ {sat_dec}  —  {max(0, total_tgt - total_ach):.1f} units still owed")
    elif "go home" in dec:
        st.success(f"✅ {sat_dec}")
    elif dec not in ("no activity", "no data"):
        st.warning(f"📋 {sat_dec}")

    st.markdown("---")
    st.subheader("📋 Task Breakdown")
    active_tasks  = df_pw[df_pw["Wk_Achieved"] > 0]
    passive_tasks = df_pw[df_pw["Wk_Achieved"] == 0]

    def render_task(row, expanded=True):
        pct = row["Pct_Real"] * 100
        lbl, badge_t, _ = status_info(pct)
        header = (f"**{row['Task']}**  —  "
                  f"{row['Wk_Achieved']:.1f} / {row['Wk_Target_Real']:.1f} units  ({pct:.1f}%)")
        with st.expander(header, expanded=expanded):
            left, right = st.columns([3, 1])
            with left:
                st.markdown("**Daily Achieved:**")
                daily = pd.DataFrame({"Day": ["Mon","Tue","Wed","Thu","Fri","Sat"],
                                      "Achieved": [row["Mon"],row["Tue"],row["Wed"],
                                                   row["Thu"],row["Fri"],row["Sat"]]})
                st.bar_chart(daily.set_index("Day"), height=200)
            with right:
                st.markdown("**Weekly:**")
                st.metric("Achieved",      f"{row['Wk_Achieved']:.1f}")
                st.metric("Target (Real)", f"{row['Wk_Target_Real']:.1f}")
                st.metric("Target (Theo)", f"{row['Wk_Target_Theo']:.1f}")
                rem = row["Wk_Target_Real"] - row["Wk_Achieved"]
                if rem > 0.01:
                    st.metric("Still Owed", f"{rem:.1f}", delta=f"{pct:.1f}%", delta_color="inverse")
                else:
                    st.metric("Remaining", "✅ Done")
                st.markdown(prog_bar(pct), unsafe_allow_html=True)
                st.markdown(f'<span class="badge {badge_t}">{lbl}</span>', unsafe_allow_html=True)

    if len(active_tasks):
        st.markdown("##### 🔥 Active Tasks")
        for _, row in active_tasks.iterrows(): render_task(row, expanded=True)
    if len(passive_tasks):
        st.markdown("##### 📌 No Activity This Week")
        for _, row in passive_tasks.iterrows(): render_task(row, expanded=False)

# ── Team overview ─────────────────────────────────────────────────────────────

def render_team(df_week, week_label_str):
    st.markdown(f"## 👥 All Crew — {week_label_str}")
    if df_week.empty:
        st.info("No data found for this week.")
        return

    def person_summary(grp):
        worked = grp[grp["Wk_Achieved"] > 0]
        ach = worked["Wk_Achieved"].sum()
        tgt = worked["Wk_Target_Real"].sum()
        return pd.Series({"total_ach": ach, "total_tgt": tgt,
                          "pct": (ach / tgt * 100) if tgt > 0 else 0.0,
                          "sat_dec": grp["Sat_Decision"].iloc[0], "active": ach > 0})

    summary = df_week.groupby("Person").apply(person_summary).reset_index()
    active_df   = summary[summary["active"]].sort_values("pct", ascending=False)
    inactive_df = summary[~summary["active"]].sort_values("Person")
    summary = pd.concat([active_df, inactive_df], ignore_index=True)

    on_track   = int((summary["pct"] >= 95).sum())
    borderline = int(((summary["pct"] >= 85) & (summary["pct"] < 95)).sum())
    need_sat   = int((summary["active"] & (summary["pct"] < 85)).sum())
    no_act     = int((~summary["active"]).sum())

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("✅ On Track (≥95%)", on_track)
    mc2.metric("⚠️ Borderline (85–94%)", borderline)
    mc3.metric("❌ Need Saturday (<85%)", need_sat)
    mc4.metric("— No Activity", no_act)
    st.markdown("---")

    cols = st.columns(4)
    for i, row in summary.iterrows():
        pct, active = row["pct"], row["active"]
        if active:
            lbl, badge, ccls = status_info(pct)
            pct_str   = f"{pct:.1f}%"
            units_str = f'{row["total_ach"]:.0f} / {row["total_tgt"]:.0f} units'
        else:
            lbl, badge, ccls = "— NO DATA", "badge-nodata", "grey"
            pct_str, units_str = "—", "No activity this week"
        with cols[i % 4]:
            st.markdown(
                f'<div class="crew-card">'
                f'<div class="crew-name">{row["Person"]}</div>'
                f'<div class="big-pct {ccls}">{pct_str}</div>'
                f'{prog_bar(pct) if active else ""}'
                f'<div style="font-size:0.8rem;color:#aaa;margin-top:0.3rem;">{units_str}</div>'
                f'<span class="badge {badge}">{lbl}</span>'
                f'</div>', unsafe_allow_html=True)

# ── Management: TASK VIEW ─────────────────────────────────────────────────────

def render_mgmt_taskview():
    st.markdown("## 🔧 Task View — All Crew Breakdown")

    df, err = load_taskview_data()
    if df is None:
        st.warning(
            f"Task View data not available yet.\n\n"
            f"In Excel: select a task in the **TASK VIEW** sheet, then run **PushAll** or **PushTaskViewSheet**.\n\n"
            f"`{err}`"
        )
        if st.button("🔄 Clear Cache to retry"):
            st.cache_data.clear()
            st.rerun()
        return

    tasks  = sorted(df["Task"].dropna().unique().tolist()) if "Task" in df.columns else []
    weeks  = sorted(df["Week_Start"].dropna().unique().tolist()) if "Week_Start" in df.columns else []
    if not tasks:
        st.warning("No tasks found. Push the TASK VIEW sheet from Excel.")
        return

    c1, c2 = st.columns(2)
    with c1: sel_task = st.selectbox("Task", tasks)
    with c2:
        sel_week = st.selectbox("Week", weeks,
                                format_func=lambda w: fmt_date(w) if w else str(w),
                                index=len(weeks) - 1 if weeks else 0)

    df_tv = df[(df["Task"] == sel_task) & (df["Week_Start"] == sel_week)].copy()
    if df_tv.empty:
        st.warning(f"No data for **{sel_task}** in week `{sel_week}`. Push the TASK VIEW sheet from Excel.")
        return

    team_row  = df_tv[df_tv.get("Is_Team_Total", pd.Series(["0"]*len(df_tv))).astype(str) == "1"]
    crew_rows = df_tv[df_tv.get("Is_Team_Total", pd.Series(["0"]*len(df_tv))).astype(str) != "1"].copy()

    day_tgt = safe_num(df_tv["Day_Target"].iloc[0]) if "Day_Target" in df_tv.columns else 0
    wk_tgt  = safe_num(df_tv["Wk_Target"].iloc[0])  if "Wk_Target"  in df_tv.columns else 0

    # ── Team summary cards ──────────────────────────────
    if len(team_row):
        tr       = team_row.iloc[0]
        team_tot = safe_num(tr.get("Wk_Total", 0), False)
        team_pct = (team_tot / wk_tgt * 100) if wk_tgt > 0 else 0.0
        lbl, badge, ccls = status_info(team_pct)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'''<div class="summary-card"><div class="label">Task</div>
<div class="value blue" style="font-size:1rem;">{sel_task}</div></div>''', unsafe_allow_html=True)
        with c2:
            st.markdown(f'''<div class="summary-card"><div class="label">Team Total This Week</div>
<div class="value {ccls}">{team_tot:.0f}</div></div>''', unsafe_allow_html=True)
        with c3:
            st.markdown(f'''<div class="summary-card"><div class="label">Weekly Target</div>
<div class="value blue">{wk_tgt:.0f}</div></div>''', unsafe_allow_html=True)
        with c4:
            st.markdown(f'''<div class="summary-card"><div class="label">Team Completion</div>
<div class="value {ccls}">{team_pct:.1f}%</div></div>''', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(prog_bar(team_pct), unsafe_allow_html=True)
        st.caption(f"Day target: **{day_tgt:.0f}** units/crew  ·  Week target: **{wk_tgt:.0f}** total units")
    st.markdown("---")

    # ── Crew cards ────────────────────────────────────────
    active_crew   = crew_rows[crew_rows["Pct_Completion"] > 0].sort_values("Pct_Completion", ascending=False)
    inactive_crew = crew_rows[crew_rows["Pct_Completion"] <= 0].sort_values("Crew_Member")

    if len(active_crew):
        st.subheader(f"🔥 Active Crew ({len(active_crew)})")
        cols = st.columns(4)
        for idx, (_, row) in enumerate(active_crew.iterrows()):
            pct      = row["Pct_Completion"]
            wk_tot   = safe_num(row.get("Wk_Total", 0))
            wk_tgt_p = safe_num(row.get("Wk_Target_Person", 0))
            lbl, badge, ccls = status_info(pct)
            with cols[idx % 4]:
                st.markdown(
                    f'''<div class="crew-card">
<div class="crew-name">{row["Crew_Member"]}</div>
<div class="big-pct {ccls}">{pct:.1f}%</div>
{prog_bar(pct)}
<div style="font-size:0.8rem;color:#aaa;margin-top:0.3rem;">{wk_tot:.1f} / {wk_tgt_p:.1f} units</div>
<span class="badge {badge}">{lbl}</span>
</div>''', unsafe_allow_html=True)

    # ── Daily breakdown table ─────────────────────────────
    if len(active_crew):
        st.markdown("---")
        st.subheader("📊 Daily Breakdown")
        show_cols = [c for c in ["Crew_Member","Mon","Tue","Wed","Thu","Fri","Sat",
                                 "Wk_Total","Wk_Target_Person","Units_Left","Pct_Completion"]
                     if c in active_crew.columns]
        df_disp = active_crew[show_cols].copy()
        for col in [c for c in show_cols if c not in ("Crew_Member",)]:
            df_disp[col] = df_disp[col].apply(
                lambda x: f"{float(x):.1f}%" if col == "Pct_Completion"
                          else (f"{float(x):.1f}" if str(x) not in ("","nan") else "—"))
        st.dataframe(df_disp.rename(columns={
            "Crew_Member":"Crew", "Wk_Total":"Week Total",
            "Wk_Target_Person":"Target", "Units_Left":"Remaining",
            "Pct_Completion":"% Done"}),
            use_container_width=True, hide_index=True)

    if "Explanation" in active_crew.columns and len(active_crew):
        with st.expander("📝 Calculation Detail", expanded=False):
            for _, row in active_crew.iterrows():
                expl = str(row.get("Explanation","")).replace(" | ","\n").strip()
                if expl and expl.lower() not in ("nan","0",""):
                    st.markdown(f"**{row['Crew_Member']}**")
                    st.code(expl, language=None)

    if len(inactive_crew):
        with st.expander(f"👻 {len(inactive_crew)} crew with no activity this week"):
            for _, row in inactive_crew.iterrows():
                st.markdown(f"- {row['Crew_Member']}")


def render_mgmt_progress():
    st.markdown("## 📊 Project Progress")

    df, err = load_progress_data()
    if df is None:
        st.warning(
            f"Progress data not available yet.\n\n"
            f"Run **PushProgressSheet** (or **PushAll**) in Excel first.\n\n`{err}`"
        )
        return

    # ── Overall summary ───────────────────────────────────
    df_raw, _ = load_tab("progress")
    overall   = pd.DataFrame()
    if df_raw is not None:
        if "Row_No" in df_raw.columns:
            overall = df_raw[df_raw["Row_No"].astype(str).str.strip() == "0"]
        elif "No" in df_raw.columns:
            overall = df_raw[df_raw["No"].astype(str).str.strip() == "0"]
        if len(overall) == 0 and "Task" in df_raw.columns:
            overall = df_raw[df_raw["Task"].astype(str).str.contains("OVERALL", case=False, na=False)]

    if len(overall):
        or_        = overall.iloc[0]
        total_req  = safe_num(or_.get("Total_Required", 0))
        total_done = safe_num(or_.get("Completed", 0))
        total_rem  = safe_num(or_.get("Remaining", 0))
        ov_pct     = safe_num(or_.get("Pct_Done", 0)) * 100
        deadline   = str(or_.get("Deadline", ""))
        days_left  = str(or_.get("Days_Left", ""))

        # Parse days_left display — strip "DAYS TO DEADLINE: " prefix if present
        days_display = days_left.replace("DAYS TO DEADLINE:", "").strip()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f'''<div class="summary-card"><div class="label">Total Required</div>
<div class="value blue">{total_req:,.0f}</div></div>''', unsafe_allow_html=True)
        with c2:
            st.markdown(
                f'''<div class="summary-card"><div class="label">Completed</div>
<div class="value green">{total_done:,.0f}</div></div>''', unsafe_allow_html=True)
        with c3:
            st.markdown(
                f'''<div class="summary-card"><div class="label">Remaining</div>
<div class="value {"amber" if total_rem > 0 else "green"}">{total_rem:,.0f}</div></div>''',
                unsafe_allow_html=True)
        with c4:
            clr = "green" if ov_pct >= 80 else ("amber" if ov_pct >= 40 else "red")
            st.markdown(
                f'''<div class="summary-card"><div class="label">Overall % Done</div>
<div class="value {clr}">{ov_pct:.1f}%</div></div>''', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(prog_bar(ov_pct), unsafe_allow_html=True)

        c5, c6 = st.columns(2)
        with c5:
            st.info(f"🗓 **Deadline:** {fmt_date(parse_date_to_iso(deadline)) if deadline else '—'}")
        with c6:
            st.info(f"⏳ **Days to Deadline:** {days_display}")
        st.markdown("---")

    # ── Task table ────────────────────────────────────────
    id_col = "Row_No" if "Row_No" in df.columns else ("No" if "No" in df.columns else None)
    display_cols = ([id_col] if id_col else []) +         [c for c in ["Task","Total_Required","Completed","Remaining",
                     "Pct_Done","Rate_2wk","Reqd_Rate","Proj_Finish","Status"]
         if c in df.columns]
    df_show = df[display_cols].copy()

    # Format numbers
    for col in ["Total_Required","Completed","Remaining"]:
        if col in df_show.columns:
            df_show[col] = df_show[col].apply(
                lambda x: f"{float(x):,.0f}" if str(x) not in ("","nan","—") else "—")
    if "Pct_Done" in df_show.columns:
        df_show["Pct_Done"] = df_show["Pct_Done"].apply(
            lambda x: f"{float(x)*100:.1f}%" if str(x) not in ("","nan","—") else "—")

    def colour_status(val):
        s = str(val)
        if "On Track"  in s: return "background-color:#1a4b2e;color:#7dffb3"
        elif "At Risk"  in s: return "background-color:#4b3a00;color:#ffd54f"
        elif "Complete" in s: return "background-color:#1a3a1a;color:#7dffb3"
        elif "Behind"   in s: return "background-color:#4b1a1a;color:#ff8a8a"
        elif "No QField" in s: return "background-color:#2a2a3e;color:#888"
        return ""

    renames = {id_col: "#", "Pct_Done": "% Done", "Rate_2wk": "Rate/day (2wk)",
               "Reqd_Rate": "Reqd Rate", "Proj_Finish": "Proj. Finish",
               "Total_Required": "Total Req", "Wk_Target_Person": "Target"}
    df_show = df_show.rename(columns={k: v for k, v in renames.items() if k in df_show.columns})

    if "Status" in df_show.columns:
        st.dataframe(df_show.style.applymap(colour_status, subset=["Status"]),
                     use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    # ── Explanation detail ─────────────────────────────────
    if "Explanation" in df.columns:
        st.markdown("---")
        st.subheader("📝 Detail per Task")
        for _, row in df.iterrows():
            status_str   = str(row.get("Status",""))
            badge_cls, icon = progress_status(status_str)
            task = str(row.get("Task",""))
            if not task or task.lower() in ("nan",""):
                continue
            with st.expander(f"{icon} **{task}** — {status_str}"):
                expl = str(row.get("Explanation","")).replace(" | ","\n")
                st.code(expl, language=None)


def render_pin_gate():
    if st.session_state.get("mgmt_auth", False):
        return True

    st.markdown("""
    <div class="pin-box">
        <h2>🔒 Management Access</h2>
        <p>This section contains detailed project data.<br>
        Enter the 4-digit PIN to continue.</p>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 1, 1])[1]
    with col:
        pin = st.text_input("PIN", type="password", max_chars=4,
                            placeholder="• • • •", label_visibility="collapsed")
        if st.button("🔓 Unlock", use_container_width=True):
            if pin == MANAGEMENT_PIN:
                st.session_state["mgmt_auth"] = True
                st.rerun()
            else:
                st.error("Incorrect PIN. Try again.")
    return False

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if "mgmt_auth" not in st.session_state:
        st.session_state["mgmt_auth"] = False

    df, err = load_crew_data()

    st.sidebar.title("🔍 Navigation")
    view = st.sidebar.radio("View", ["👤 Individual", "👥 Team Overview", "🔒 Management"])

    sel_week = None; sel_week_lbl = ""; sel_person = None
    week_labels = {}; persons = []; latest = ""

    if df is not None:
        weeks_raw   = sorted(df["Week_Start"].dropna().unique())
        week_labels = {w: f"{fmt_date(w)}  (Week {i+1})" for i, w in enumerate(weeks_raw)}
        week_options = list(week_labels.values())
        persons     = sorted(df["Person"].unique().tolist())
        latest      = weeks_raw[-1] if weeks_raw else ""

        if view in ("👤 Individual", "👥 Team Overview"):
            st.sidebar.markdown("**Select Week:**")
            sel_week_lbl = st.sidebar.selectbox(
                "", week_options, index=len(week_options)-1, label_visibility="collapsed")
            sel_week = next(w for w, lbl in week_labels.items() if lbl == sel_week_lbl)

        if view == "👤 Individual":
            st.sidebar.markdown("**Select Person:**")
            sel_person = st.sidebar.selectbox("", persons, label_visibility="collapsed")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "**Daily workflow:**\n\n"
        "1. Import QField → Excel\n"
        "2. Run **RefreshAppSheet**\n"
        "3. Run **PushAll**\n"
        "4. Click Reload ↓"
    )
    if df is not None:
        st.sidebar.caption(f"📊 {len(df)} rows · {len(week_labels)} weeks\n\n"
                           f"🕒 {datetime.now().strftime('%I:%M %p, %d %b %Y')}")
    if st.sidebar.button("🔄 Clear Cache & Reload"):
        st.cache_data.clear()
        st.session_state["mgmt_auth"] = False
        st.rerun()

    st.markdown(
        f'<div class="main-header">'
        f'<h1>🎯 Fulham Solar Farm — Weekly Targets</h1>'
        f'<p>Latest data: {fmt_date(latest) if latest else "—"}'
        f'  ·  {len(week_labels)} week{"s" if len(week_labels) != 1 else ""} tracked'
        f'  ·  {len(persons)} crew members</p>'
        f'</div>', unsafe_allow_html=True)

    if view == "🔒 Management":
        if not render_pin_gate():
            return

        st.markdown(
            '<div class="mgmt-header">'
            '<span style="font-size:1.2rem;font-weight:700;">🔒 Management Dashboard</span>'
            '<span style="font-size:0.85rem;opacity:0.7;">Restricted access</span>'
            '</div>', unsafe_allow_html=True)

        mgmt_tab = st.radio(
            "Section", ["🔧 Task View", "📊 Project Progress"],
            horizontal=True
        )
        if mgmt_tab == "🔧 Task View":
            render_mgmt_taskview()
        else:
            render_mgmt_progress()

        st.markdown("---")
        if st.button("🔒 Lock Management Area"):
            st.session_state["mgmt_auth"] = False
            st.rerun()
        return

    if df is None:
        st.error(f"Could not load crew data.\n\n`{err}`\n\n"
                 "Check the sheet is shared and PushAll has been run.")
        return

    if view == "👥 Team Overview":
        df_week = df[df["Week_Start"] == sel_week].copy()
        render_team(df_week, sel_week_lbl)
    else:
        if sel_person is None:
            st.info("Select a person from the sidebar.")
        else:
            df_pw = df[(df["Week_Start"] == sel_week) & (df["Person"] == sel_person)].copy()
            if len(df_pw) == 0:
                all_weeks = sorted(df[df["Person"] == sel_person]["Week_Start"].unique())
                st.warning(f"No data for **{sel_person}** in week `{sel_week}`.\n\n"
                           f"Weeks found: `{all_weeks}`")
            else:
                render_individual(df_pw, sel_person)


if __name__ == "__main__":
    main()
