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
</style>
""", unsafe_allow_html=True)

# ── Google Sheet IDs ──────────────────────────────────────────────────────────
SHEET_ID = "1_eWq5Mx9zBfKfkqP56wqH3uLnwbv3k714t0dztzOEo4"
def sheet_url(tab): return (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/export?format=csv&sheet={tab}"
)

MANAGEMENT_PIN = "1999"

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
    if not s or s.lower() == "nan": return 0.0
    if s.endswith("%"):
        try:    return float(s[:-1]) / 100.0
        except: return 0.0
    if s.count(".") >= 2:
        digits = s.replace(".", "")
        try:
            val = float(digits) / 1e12
            if is_daily and val > 500:
                val = val / 10.0
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
def load_targets_data():
    df, err = load_tab("targets")
    if df is None: return None, err
    if "Person" not in df.columns: return None, "targets tab not pushed yet."
    df = df[df["Person"].astype(str).str.strip() != ""].copy()
    df["Week_Start"] = df.get("Week_Start", pd.Series()).apply(parse_date_to_iso)
    for col in ["Mon_Ach","Tue_Ach","Wed_Ach","Thu_Ach","Fri_Ach","Sat_Ach"]:
        if col in df.columns: df[col] = df[col].apply(lambda v: safe_num(v, True))
    for col in ["Wk_Achieved","Wk_Target_Real","Wk_Target_Theo","Pct_Real","Remaining_Pct"]:
        if col in df.columns: df[col] = df[col].apply(lambda v: safe_num(v, False))
    df["Pct_Real"] = df.apply(
        lambda r: safe_num(r.get("Pct_Real", 0), False), axis=1)
    return df, None

@st.cache_data(ttl=300)
def load_progress_data():
    df, err = load_tab("progress")
    if df is None: return None, err
    if "Task" not in df.columns: return None, "progress tab not pushed yet."
    # Skip summary row
    df = df[df["No"].astype(str).str.strip() != "0"].copy()
    df = df[df["Task"].astype(str).str.strip() != ""].copy()
    for col in ["Total_Required","Completed","Remaining"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "Pct_Done" in df.columns:
        df["Pct_Done"] = df["Pct_Done"].apply(lambda v: safe_num(v, False))
    return df, None


# ── Individual crew view ──────────────────────────────────────────────────────

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


# ── Management: TARGETS detail view ──────────────────────────────────────────

def render_mgmt_targets():
    st.markdown("## 📋 Targets — Full Breakdown")
    df, err = load_targets_data()
    if df is None:
        st.warning(f"Targets data not available yet.\n\n"
                   f"Run **PushTargetsSheet** in Excel first.\n\n`{err}`")
        return

    # Show header info
    persons = df[df["Person"] != "SUMMARY"]["Person"].unique().tolist()
    weeks   = sorted(df["Week_Start"].dropna().unique().tolist())

    col1, col2 = st.columns(2)
    with col1:
        sel_person = st.selectbox("Person", persons)
    with col2:
        sel_week   = st.selectbox("Week", weeks,
                                  format_func=lambda w: fmt_date(w) if w else str(w),
                                  index=len(weeks)-1)

    df_pw = df[(df["Person"] == sel_person) & (df["Week_Start"] == sel_week) &
               (df["Person"] != "SUMMARY")].copy()
    summary_row = df[(df["Person"] == "SUMMARY") & (df["Week_Start"] == sel_week)]

    if len(df_pw) == 0:
        st.warning("No data for this person/week. Run PushTargetsSheet from TARGETS view.")
        return

    # Summary banner
    if len(summary_row):
        sr = summary_row.iloc[0]
        total_u = safe_num(sr.get("Wk_Achieved", 0), False)
        avg_pct = safe_num(sr.get("Pct_Real", 0),    False) * 100
        sat_dec = str(sr.get("Block_Breakdown", sr.get("Explanation",""))).split("|")[0].strip()
        days    = str(sr.get("Pace_vs_Deadline", ""))
    else:
        active  = df_pw[df_pw["Wk_Achieved"] > 0]
        total_u = active["Wk_Achieved"].sum()
        tgt_u   = active["Wk_Target_Real"].sum()
        avg_pct = (total_u / tgt_u * 100) if tgt_u > 0 else 0.0
        sat_dec = df_pw["Block_Breakdown"].iloc[0] if "Block_Breakdown" in df_pw.columns else ""
        days    = ""

    lbl, badge, ccls = status_info(avg_pct)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="summary-card"><div class="label">Total Units</div>'
                    f'<div class="value {ccls}">{total_u:.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="summary-card"><div class="label">Completion</div>'
                    f'<div class="value {ccls}">{avg_pct:.1f}%</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="summary-card"><div class="label">Saturday</div>'
                    f'<div class="value" style="font-size:0.9rem;padding-top:0.8rem;">'
                    f'<span class="badge {badge}">{lbl}</span></div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="summary-card"><div class="label">Days to Deadline</div>'
                    f'<div class="value grey">{days}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # Full task table with explanation
    st.subheader("Task Detail")
    day_cols = [c for c in ["Mon_Ach","Tue_Ach","Wed_Ach","Thu_Ach","Fri_Ach","Sat_Ach"] if c in df_pw.columns]
    display_cols = ["Task"] + day_cols + ["Wk_Achieved","Wk_Target_Real","Pct_Real","Pace_vs_Deadline","Block_Breakdown"]
    display_cols = [c for c in display_cols if c in df_pw.columns]

    df_show = df_pw[df_pw["Wk_Achieved"] > 0][display_cols].copy()
    if len(df_show) == 0:
        st.info("No active tasks this week for the loaded person.")
        df_show = df_pw[display_cols].copy()

    if "Pct_Real" in df_show.columns:
        df_show["Pct_Real"] = (df_show["Pct_Real"] * 100).round(1).astype(str) + "%"

    st.dataframe(df_show.rename(columns={
        "Mon_Ach":"Mon","Tue_Ach":"Tue","Wed_Ach":"Wed","Thu_Ach":"Thu","Fri_Ach":"Fri","Sat_Ach":"Sat",
        "Wk_Achieved":"Achieved","Wk_Target_Real":"Target","Pct_Real":"Pct%",
        "Pace_vs_Deadline":"Pace","Block_Breakdown":"Blocks"
    }), use_container_width=True, hide_index=True)

    # Explanation detail per task
    if "Explanation" in df_pw.columns:
        active_expl = df_pw[df_pw["Wk_Achieved"] > 0]
        if len(active_expl):
            st.markdown("---")
            st.subheader("📝 Calculation Detail")
            for _, row in active_expl.iterrows():
                with st.expander(f"**{row['Task']}**"):
                    st.code(str(row.get("Explanation", "")).replace(" | ", "\n"), language=None)


# ── Management: PROJECT PROGRESS view ────────────────────────────────────────

def render_mgmt_progress():
    st.markdown("## 📊 Project Progress")
    df, err = load_progress_data()
    if df is None:
        st.warning(f"Progress data not available yet.\n\n"
                   f"Run **PushProgressSheet** in Excel first.\n\n`{err}`")
        return

    # Load overall summary from the raw tab (row 0 = summary)
    df_raw, _ = load_tab("progress")
    if df_raw is not None and "No" in df_raw.columns:
        overall = df_raw[df_raw["No"].astype(str).str.strip() == "0"]
        if len(overall):
            or_ = overall.iloc[0]
            total_req  = safe_num(or_.get("Total_Required", 0))
            total_done = safe_num(or_.get("Completed", 0))
            total_rem  = safe_num(or_.get("Remaining", 0))
            ov_pct     = safe_num(or_.get("Pct_Done", 0)) * 100
            deadline   = str(or_.get("Deadline", ""))
            days_left  = str(or_.get("Days_Left", ""))

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="summary-card"><div class="label">Total Required</div>'
                            f'<div class="value blue">{total_req:,.0f}</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="summary-card"><div class="label">Completed</div>'
                            f'<div class="value green">{total_done:,.0f}</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="summary-card"><div class="label">Overall % Done</div>'
                            f'<div class="value {"green" if ov_pct >= 50 else "amber"}">'
                            f'{ov_pct:.1f}%</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="summary-card"><div class="label">Deadline / Days Left</div>'
                            f'<div class="value grey" style="font-size:1rem;">'
                            f'{deadline}<br><span style="font-size:1.4rem;">{days_left}</span>'
                            f'</div></div>', unsafe_allow_html=True)

            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(prog_bar(ov_pct), unsafe_allow_html=True)
            st.markdown("---")

    # Task table
    display_cols = ["No","Task","Total_Required","Completed","Remaining","Pct_Done",
                    "Rate_2wk","Reqd_Rate","Proj_Finish","Status"]
    display_cols = [c for c in display_cols if c in df.columns]
    df_show = df[display_cols].copy()

    if "Pct_Done" in df_show.columns:
        df_show["Pct_Done"] = (df_show["Pct_Done"] * 100).round(1).astype(str) + "%"

    # Colour-code Status column using styled dataframe
    def colour_status(val):
        s = str(val)
        if "On Track" in s:  return "background-color:#1a4b2e;color:#7dffb3"
        elif "At Risk" in s: return "background-color:#4b3a00;color:#ffd54f"
        elif "Complete" in s: return "background-color:#1a3a1a;color:#7dffb3"
        elif "Behind" in s:  return "background-color:#4b1a1a;color:#ff8a8a"
        return ""

    if "Status" in df_show.columns:
        st.dataframe(
            df_show.style.applymap(colour_status, subset=["Status"]),
            use_container_width=True, hide_index=True
        )
    else:
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    # Explanation detail
    if "Explanation" in df.columns:
        st.markdown("---")
        st.subheader("📝 Calculation Detail")
        for _, row in df.iterrows():
            status_str = str(row.get("Status",""))
            badge_cls, icon = progress_status(status_str)
            task = str(row.get("Task",""))
            with st.expander(f"{icon} **{task}** — {status_str}"):
                expl = str(row.get("Explanation","")).replace(" | ", "\n")
                st.code(expl, language=None)


# ── PIN gate ──────────────────────────────────────────────────────────────────

def render_pin_gate():
    """Show PIN entry in the main area. Returns True if authenticated."""
    if st.session_state.get("mgmt_auth", False):
        return True

    st.markdown("""
    <div class="pin-box">
        <h2>🔒 Management Access</h2>
        <p>This section contains detailed project and targets data.<br>
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
    # Initialise session state
    if "mgmt_auth" not in st.session_state:
        st.session_state["mgmt_auth"] = False

    df, err = load_crew_data()

    # ── Sidebar ──────────────────────────────────────────────
    st.sidebar.title("🔍 Navigation")

    view = st.sidebar.radio("View", [
        "👤 Individual",
        "👥 Team Overview",
        "🔒 Management"
    ])

    # Build week/person selectors only if crew data loaded
    sel_week     = None
    sel_week_lbl = ""
    sel_person   = None
    week_labels  = {}
    persons      = []
    latest       = ""

    if df is not None:
        weeks_raw    = sorted(df["Week_Start"].dropna().unique())
        week_labels  = {w: f"{fmt_date(w)}  (Week {i+1})" for i, w in enumerate(weeks_raw)}
        week_options = list(week_labels.values())
        persons      = sorted(df["Person"].unique().tolist())
        latest       = weeks_raw[-1] if weeks_raw else ""

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
        "3. Run **PushAll** *(or individual push macros)*\n"
        "4. Click Reload ↓"
    )
    if df is not None:
        st.sidebar.caption(f"📊 {len(df)} rows · "
                           f"{len(week_labels)} weeks\n\n"
                           f"🕒 {datetime.now().strftime('%I:%M %p, %d %b %Y')}")
    if st.sidebar.button("🔄 Clear Cache & Reload"):
        st.cache_data.clear()
        st.session_state["mgmt_auth"] = False
        st.rerun()

    # ── Header ───────────────────────────────────────────────
    st.markdown(
        f'<div class="main-header">'
        f'<h1>🎯 Fulham Solar Farm — Weekly Targets</h1>'
        f'<p>Latest data: {fmt_date(latest) if latest else "—"}'
        f'  ·  {len(week_labels)} week{"s" if len(week_labels) != 1 else ""} tracked'
        f'  ·  {len(persons)} crew members</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Route ────────────────────────────────────────────────
    if view == "🔒 Management":
        if not render_pin_gate():
            return   # show PIN form, stop here

        # Authenticated — show management sub-tabs
        st.markdown(
            '<div class="mgmt-header">'
            '<span style="font-size:1.2rem;font-weight:700;">🔒 Management Dashboard</span>'
            '<span style="font-size:0.85rem;opacity:0.7;">Restricted access</span>'
            '</div>',
            unsafe_allow_html=True
        )

        mgmt_tab = st.radio(
            "Section", ["📋 Targets Detail", "📊 Project Progress"],
            horizontal=True
        )

        if mgmt_tab == "📋 Targets Detail":
            render_mgmt_targets()
        else:
            render_mgmt_progress()

        # Lock button
        st.markdown("---")
        if st.button("🔒 Lock Management Area"):
            st.session_state["mgmt_auth"] = False
            st.rerun()
        return

    # ── Public views ─────────────────────────────────────────
    if df is None:
        st.error(f"Could not load crew data.\n\n`{err}`\n\n"
                 "Check the sheet is shared and PushToGoogleSheets has been run.")
        return

    if view == "👥 Team Overview":
        df_week = df[df["Week_Start"] == sel_week].copy()
        render_team(df_week, sel_week_lbl)

    else:  # Individual
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
