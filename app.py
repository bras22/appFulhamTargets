import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

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
    .crew-card .crew-name { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem; color: #e0e0e0; }
    .crew-card .big-pct   { font-size: 2rem; font-weight: 800; line-height: 1; }
    .badge { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 20px;
             font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; margin-top: 0.4rem; }
    .badge-go     { background: #1a6b3a; color: #7dffb3; }
    .badge-border { background: #6b5a00; color: #ffe57d; }
    .badge-stay   { background: #6b1a1a; color: #ff8a8a; }
    .badge-nodata { background: #333;    color: #aaa; }
    .green { color: #4dff91; }
    .amber { color: #ffd54f; }
    .red   { color: #ff6b6b; }
    .grey  { color: #888; }
    .prog-wrap { background: #2a2a3e; border-radius: 6px; height: 12px; overflow: hidden; margin: 0.4rem 0; }
    .prog-bar  { height: 100%; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)


# ── Google Sheet published as CSV ─────────────────────────────────────────────
# File > Share > Publish to web > Sheet "app" > CSV
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1_eWq5Mx9zBfKfkqP56wqH3uLnwbv3k714t0dztzOEo4/edit?usp=sharing"


# ─────────────────────────────────────────────────────────────────────────────

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


def fmt_date(d):
    if isinstance(d, datetime): d = d.date()
    if isinstance(d, date):     return d.strftime("%d %b %Y")
    return str(d)


@st.cache_data(ttl=300)
def load_app_sheet(_unused=None):
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
    except Exception as e:
        st.error(f"Cannot load Google Sheet: {e}")
        return None

    if df.empty:
        st.error("Google Sheet 'app' is empty — run RefreshAppSheet in Excel and push first.")
        return None

    # Strip column names
    df.columns = [str(c).strip() for c in df.columns]

    # Drop metadata rows (e.g. "Last refreshed...")
    if "Person" in df.columns:
        df = df[df["Person"].notna()]
        df = df[~df["Person"].astype(str).str.startswith("Last refreshed")]

    # Parse Week_Start
    def to_date(v):
        if isinstance(v, datetime): return v.date()
        if isinstance(v, date):     return v
        try:    return pd.to_datetime(v, dayfirst=True).date()
        except: return None

    if "Week_Start" in df.columns:
        df["Week_Start"] = df["Week_Start"].apply(to_date)

    for col in ["Mon","Tue","Wed","Thu","Fri","Sat","Wk_Achieved","Wk_Target_Real",
                "Wk_Target_Theo","Pct_Real","Remaining_Units","Days_To_Deadline"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["Person"]       = df["Person"].astype(str).str.strip()
    df["Task"]         = df["Task"].astype(str).str.strip()
    df["Sat_Decision"] = df["Sat_Decision"].astype(str).str.strip()
    return df


def get_data():
    return load_app_sheet()


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
        st.markdown(f'<div class="summary-card"><div class="label">Total Units</div>'
                    f'<div class="value {ccls}">{total_ach:.0f}</div></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="summary-card"><div class="label">Avg Completion</div>'
                    f'<div class="value {ccls}">{avg_pct:.1f}%</div></div>',
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="summary-card"><div class="label">Saturday</div>'
                    f'<div class="value" style="font-size:0.9rem;padding-top:0.8rem;">'
                    f'<span class="badge {badge}">{label}</span></div></div>',
                    unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="summary-card"><div class="label">Days to Deadline</div>'
                    f'<div class="value grey">{days_left}</div></div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    dec_lower = sat_dec.lower()
    if "saturday required" in dec_lower:
        st.error(f"⚠️ {sat_dec}  —  {max(0, total_tgt - total_ach):.0f} units still owed")
    elif "go home" in dec_lower:
        st.success(f"✅ {sat_dec}")
    elif dec_lower not in ("no activity", "no data"):
        st.warning(f"📋 {sat_dec}")

    st.markdown("---")
    st.subheader("📋 Task Breakdown")

    active_tasks  = df_pw[df_pw["Wk_Achieved"] > 0]
    passive_tasks = df_pw[df_pw["Wk_Achieved"] == 0]

    def render_task(row, expanded=True):
        pct = row["Pct_Real"] * 100 if row["Pct_Real"] <= 1.5 else row["Pct_Real"]
        lbl, badge_t, col_t = status_info(pct)
        header = (f"**{row['Task']}**  —  "
                  f"{row['Wk_Achieved']:.0f} / {row['Wk_Target_Real']:.0f} "
                  f"({pct:.1f}%)")
        with st.expander(header, expanded=expanded):
            left, right = st.columns([3, 1])
            with left:
                st.markdown("**Daily Achieved:**")
                daily = pd.DataFrame({
                    "Day":      ["Mon","Tue","Wed","Thu","Fri","Sat"],
                    "Achieved": [row["Mon"],row["Tue"],row["Wed"],
                                 row["Thu"],row["Fri"],row["Sat"]]
                })
                st.bar_chart(daily.set_index("Day"), height=200)
            with right:
                st.markdown("**Weekly:**")
                st.metric("Achieved",      f"{row['Wk_Achieved']:.0f}")
                st.metric("Target (Real)", f"{row['Wk_Target_Real']:.0f}")
                st.metric("Target (Theo)", f"{row['Wk_Target_Theo']:.0f}")
                rem = row["Wk_Target_Real"] - row["Wk_Achieved"]
                if rem > 0:
                    st.metric("Still Owed", f"{rem:.0f}",
                              delta=f"{pct:.1f}%", delta_color="inverse")
                else:
                    st.metric("Remaining", "✅ Done")
                st.markdown(prog_bar(pct), unsafe_allow_html=True)
                st.markdown(f'<span class="badge {badge_t}">{lbl}</span>',
                            unsafe_allow_html=True)

    if len(active_tasks):
        st.markdown("##### 🔥 Active Tasks")
        for _, row in active_tasks.iterrows():
            render_task(row, expanded=True)

    if len(passive_tasks):
        st.markdown("##### 📌 No Activity This Week")
        for _, row in passive_tasks.iterrows():
            render_task(row, expanded=False)


def render_team(df_week, week_label_str):
    st.markdown(f"## 👥 All Crew — {week_label_str}")

    active = df_week[df_week["Wk_Achieved"] > 0]
    all_persons    = sorted(df_week["Person"].unique())
    active_persons = active["Person"].unique() if len(active) else []

    if len(active) == 0:
        st.info("No QField activity recorded for this week yet.")
        return

    summary = (active.groupby("Person")
               .agg(total_ach=("Wk_Achieved","sum"),
                    total_tgt=("Wk_Target_Real","sum"),
                    sat_dec  =("Sat_Decision","first"))
               .reset_index())
    summary["pct"] = summary.apply(
        lambda r: r["total_ach"]/r["total_tgt"]*100 if r["total_tgt"] > 0 else 0, axis=1)
    summary = summary.sort_values("pct", ascending=False).reset_index(drop=True)

    inactive = [p for p in all_persons if p not in list(active_persons)]

    on_track   = int((summary["pct"] >= 95).sum())
    borderline = int(((summary["pct"] >= 85) & (summary["pct"] < 95)).sum())
    need_sat   = int((summary["pct"] < 85).sum())

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("✅ On Track (≥95%)",     on_track)
    mc2.metric("⚠️ Borderline (85–94%)", borderline)
    mc3.metric("❌ Need Saturday (<85%)", need_sat)
    mc4.metric("— No Activity",          len(inactive))

    st.markdown("---")

    cols = st.columns(4)
    for i, row in summary.iterrows():
        pct = row["pct"]
        lbl, badge, ccls = status_info(pct)
        with cols[i % 4]:
            st.markdown(f"""
            <div class="crew-card">
                <div class="crew-name">{row['Person']}</div>
                <div class="big-pct {ccls}">{pct:.1f}%</div>
                {prog_bar(pct)}
                <div style="font-size:0.8rem;color:#aaa;margin-top:0.3rem;">
                    {row['total_ach']:.0f} / {row['total_tgt']:.0f} units
                </div>
                <span class="badge {badge}">{lbl}</span>
            </div>""", unsafe_allow_html=True)

    if inactive:
        st.markdown("---")
        with st.expander(f"👻 {len(inactive)} crew with no activity this week"):
            for name in sorted(inactive):
                st.markdown(f"- {name}")


def main():
    df = get_data()
    if df is None:
        st.error("No data could be loaded.")
        return

    if "Week_Start" not in df.columns:
        st.error("Column 'Week_Start' missing. Run RefreshAppSheet in Excel and push again.")
        return

    weeks_raw = sorted(df["Week_Start"].dropna().unique())
    if not weeks_raw:
        st.error("No week data found.")
        return

    week_labels  = {w: f"{fmt_date(w)}  (Week {i+1})" for i, w in enumerate(weeks_raw)}
    week_options = list(week_labels.values())
    persons      = sorted(df["Person"].unique().tolist())

    latest = weeks_raw[-1]
    st.markdown(f"""
    <div class="main-header">
        <h1>🎯 Fulham Solar Farm — Weekly Targets</h1>
        <p>Latest data: {fmt_date(latest)}  ·  {len(weeks_raw)} weeks tracked  ·  {len(persons)} crew</p>
    </div>""", unsafe_allow_html=True)

    st.sidebar.title("🔍 Navigation")
    view = st.sidebar.radio("View", ["👤 Individual", "👥 Team Overview"])

    st.sidebar.markdown("**Week:**")
    sel_week_lbl = st.sidebar.selectbox(
        "", week_options, index=len(week_options)-1, label_visibility="collapsed")
    sel_week = next(w for w, lbl in week_labels.items() if lbl == sel_week_lbl)

    sel_person = None
    if view == "👤 Individual":
        st.sidebar.markdown("**Person:**")
        sel_person = st.sidebar.selectbox("", persons, label_visibility="collapsed")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "After each daily QField import, open Excel and run  \n"
        "**RefreshAppSheet → Push to Google Sheets** to update."
    )
    st.sidebar.caption(f"🕒 {datetime.now().strftime('%I:%M %p, %d %b %Y')}")
    if st.sidebar.button("🔄 Clear Cache & Reload"):
        st.cache_data.clear()
        st.rerun()

    df_week = df[df["Week_Start"] == sel_week].copy()

    if view == "👥 Team Overview":
        render_team(df_week, week_label_str=sel_week_lbl)
    else:
        df_pw = df_week[df_week["Person"] == sel_person].copy()
        if len(df_pw) == 0:
            st.warning(f"No data for **{sel_person}** in {sel_week_lbl}.")
        else:
            render_individual(df_pw, sel_person)


if __name__ == "__main__":
    main()
