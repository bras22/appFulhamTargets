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
    .green { color:#4dff91; } .amber { color:#ffd54f; }
    .red   { color:#ff6b6b; } .grey  { color:#888; }
    .prog-wrap { background:#2a2a3e; border-radius:6px; height:12px; overflow:hidden; margin:0.4rem 0; }
    .prog-bar  { height:100%; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

# ── Google Sheet (must be shared as "Anyone with the link → Viewer") ──────────
SHEET_ID = "1_eWq5Mx9zBfKfkqP56wqH3uLnwbv3k714t0dztzOEo4"
CSV_URL  = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            f"/export?format=csv&sheet=app")

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
    """
    Convert any date value to 'YYYY-MM-DD' string.
    VBA CStr() with Australian locale writes dates as 'D/MM/YYYY'.
    We try formats in priority order — ISO first (most reliable).
    """
    if v is None: return None
    s = str(v).strip()
    if not s or s.lower() == "nan": return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except: pass
    try:    return pd.to_datetime(s, dayfirst=False).strftime("%Y-%m-%d")
    except: return None

def safe_num(v, is_daily=False):
    """
    Parse a cell value that may be:
    - a plain float:       "286.33"
    - a percentage string: "34.0%"
    - a European-thousands-corrupted number: "303.333.333.333.333"
      (caused by VBA CStr() using locale comma as decimal, then Google Sheets
       misreading comma as thousands separator and re-exporting with dot separators)
    
    The fix_vba flag: once PushToGoogleSheets uses Str() instead of CStr(),
    these corrupted values will no longer appear.  This function handles
    both old (corrupt) and new (clean) data.

    is_daily=True: column is Mon/Tue/Wed/Thu/Fri/Sat (max ~700/person/day).
                   Values > 500 after the ÷10^12 recovery are divided by 10.
    is_daily=False: column is a weekly aggregate (max ~5000). No ÷10.
    """
    if v is None: return 0.0
    s = str(v).strip()
    if not s or s.lower() == "nan": return 0.0

    if s.endswith("%"):
        try:    return float(s[:-1]) / 100.0
        except: return 0.0

    # Detect corrupted European-thousands format: two or more dots
    if s.count(".") >= 2:
        digits = s.replace(".", "")
        try:
            N = float(digits)
            val = N / 1e12   # restore 15-significant-digit double
            if is_daily and val > 500:
                # Daily value > 500 means the ÷10^12 result is 10x too large.
                # Divide by 10 to recover the true value.
                val = val / 10.0
            return val
        except:
            pass

    try:    return float(s)
    except: return 0.0


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, dtype=str, on_bad_lines="skip")
    except Exception as e:
        st.error(
            "❌ Cannot load Google Sheet.\n\n"
            "**Check:** File → Share → *Anyone with the link → Viewer*\n\n"
            f"`{e}`"
        )
        return None

    if df.empty:
        st.error("Sheet 'app' is empty — run RefreshAppSheet then PushToGoogleSheets in Excel.")
        return None

    df.columns = [str(c).strip() for c in df.columns]

    if "Person" not in df.columns:
        st.error(f"Column 'Person' not found. Columns: `{df.columns.tolist()[:10]}`")
        return None

    # Drop blank / timestamp rows
    df = df[df["Person"].notna()].copy()
    df = df[df["Person"].astype(str).str.strip() != ""].copy()
    df = df[~df["Person"].astype(str).str.startswith("Last refreshed")].copy()

    # Parse Week_Start → canonical ISO string "YYYY-MM-DD"
    # Stored as string avoids ALL pandas date comparison issues.
    if "Week_Start" not in df.columns:
        st.error("Column 'Week_Start' not found.")
        return None
    df["Week_Start"] = df["Week_Start"].apply(parse_date_to_iso)
    df = df[df["Week_Start"].notna()].copy()

    # Daily columns (Mon–Sat): max per-person per-day ≈ 700 → is_daily=True
    daily_cols   = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    weekly_cols  = ["Wk_Achieved", "Wk_Target_Real", "Wk_Target_Theo",
                    "Pct_Real", "Remaining_Units", "Days_To_Deadline"]

    for col in daily_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: safe_num(v, is_daily=True))

    for col in weekly_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: safe_num(v, is_daily=False))

    # Recalculate Pct_Real from raw columns (don't trust the stored value)
    df["Pct_Real"] = df.apply(
        lambda r: r["Wk_Achieved"] / r["Wk_Target_Real"]
        if r["Wk_Target_Real"] > 0 else 0.0, axis=1)

    df["Person"]       = df["Person"].astype(str).str.strip()
    df["Task"]         = df["Task"].astype(str).str.strip()
    df["Sat_Decision"] = df["Sat_Decision"].astype(str).str.strip() \
                         if "Sat_Decision" in df.columns else "No data"
    return df


# ── Individual view ───────────────────────────────────────────────────────────

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
                    f'<div class="value {ccls}">{total_ach:.1f}</div></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="summary-card"><div class="label">Avg Completion</div>'
                    f'<div class="value {ccls}">{avg_pct:.1f}%</div></div>',
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="summary-card"><div class="label">Saturday Decision</div>'
                    f'<div class="value" style="font-size:0.9rem;padding-top:0.8rem;">'
                    f'<span class="badge {badge}">{label}</span></div></div>',
                    unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="summary-card"><div class="label">Days to Deadline</div>'
                    f'<div class="value grey">{days_left}</div></div>',
                    unsafe_allow_html=True)

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
                  f"{row['Wk_Achieved']:.1f} / {row['Wk_Target_Real']:.1f} units  "
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
                st.metric("Achieved",      f"{row['Wk_Achieved']:.1f}")
                st.metric("Target (Real)", f"{row['Wk_Target_Real']:.1f}")
                st.metric("Target (Theo)", f"{row['Wk_Target_Theo']:.1f}")
                rem = row["Wk_Target_Real"] - row["Wk_Achieved"]
                if rem > 0.01:
                    st.metric("Still Owed", f"{rem:.1f}",
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


# ── Team overview ─────────────────────────────────────────────────────────────

def render_team(df_week, week_label_str):
    st.markdown(f"## 👥 All Crew — {week_label_str}")

    if df_week.empty:
        st.info("No data found for this week.")
        return

    def person_summary(grp):
        worked = grp[grp["Wk_Achieved"] > 0]
        ach    = worked["Wk_Achieved"].sum()
        tgt    = worked["Wk_Target_Real"].sum()
        pct    = (ach / tgt * 100) if tgt > 0 else 0.0
        return pd.Series({
            "total_ach": ach,
            "total_tgt": tgt,
            "pct":       pct,
            "sat_dec":   grp["Sat_Decision"].iloc[0],
            "active":    ach > 0,
        })

    summary = df_week.groupby("Person").apply(person_summary).reset_index()

    active_df   = summary[summary["active"]].sort_values("pct", ascending=False)
    inactive_df = summary[~summary["active"]].sort_values("Person")
    summary     = pd.concat([active_df, inactive_df], ignore_index=True)

    on_track   = int((summary["pct"] >= 95).sum())
    borderline = int(((summary["pct"] >= 85) & (summary["pct"] < 95)).sum())
    need_sat   = int((summary["active"] & (summary["pct"] < 85)).sum())
    no_act     = int((~summary["active"]).sum())

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("✅ On Track (≥95%)",      on_track)
    mc2.metric("⚠️ Borderline (85–94%)",  borderline)
    mc3.metric("❌ Need Saturday (<85%)", need_sat)
    mc4.metric("— No Activity",           no_act)

    st.markdown("---")

    cols = st.columns(4)
    for i, row in summary.iterrows():
        pct    = row["pct"]
        active = row["active"]
        if active:
            lbl, badge, ccls = status_info(pct)
            pct_str   = f"{pct:.1f}%"
            units_str = f'{row["total_ach"]:.0f} / {row["total_tgt"]:.0f} units'
        else:
            lbl, badge, ccls = "— NO DATA", "badge-nodata", "grey"
            pct_str   = "—"
            units_str = "No activity this week"

        with cols[i % 4]:
            st.markdown(
                f'<div class="crew-card">'
                f'<div class="crew-name">{row["Person"]}</div>'
                f'<div class="big-pct {ccls}">{pct_str}</div>'
                f'{prog_bar(pct) if active else ""}'
                f'<div style="font-size:0.8rem;color:#aaa;margin-top:0.3rem;">{units_str}</div>'
                f'<span class="badge {badge}">{lbl}</span>'
                f'</div>',
                unsafe_allow_html=True
            )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    df = load_data()
    if df is None:
        st.stop()

    weeks_raw = sorted(df["Week_Start"].dropna().unique())
    if not weeks_raw:
        st.error("No week data found.")
        st.stop()

    # Week_Start is stored as "YYYY-MM-DD" strings — compare as strings
    week_labels  = {w: f"{fmt_date(w)}  (Week {i+1})" for i, w in enumerate(weeks_raw)}
    week_options = list(week_labels.values())
    persons      = sorted(df["Person"].unique().tolist())
    latest       = weeks_raw[-1]

    st.markdown(
        f'<div class="main-header">'
        f'<h1>🎯 Fulham Solar Farm — Weekly Targets</h1>'
        f'<p>Latest data: {fmt_date(latest)}'
        f'  ·  {len(weeks_raw)} week{"s" if len(weeks_raw) != 1 else ""} tracked'
        f'  ·  {len(persons)} crew members</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.sidebar.title("🔍 Navigation")
    view = st.sidebar.radio("View", ["👤 Individual", "👥 Team Overview"])

    st.sidebar.markdown("**Select Week:**")
    sel_week_lbl = st.sidebar.selectbox(
        "", week_options, index=len(week_options)-1, label_visibility="collapsed")
    sel_week = next(w for w, lbl in week_labels.items() if lbl == sel_week_lbl)

    sel_person = None
    if view == "👤 Individual":
        st.sidebar.markdown("**Select Person:**")
        sel_person = st.sidebar.selectbox("", persons, label_visibility="collapsed")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "**Daily update workflow:**\n\n"
        "1. Import QField data into Excel\n"
        "2. Run **RefreshAppSheet** macro\n"
        "3. Run **PushToGoogleSheets** macro\n"
        "4. Click Reload ↓"
    )
    st.sidebar.caption(f"📊 {len(df)} rows · {len(weeks_raw)} weeks\n\n"
                       f"🕒 {datetime.now().strftime('%I:%M %p, %d %b %Y')}")
    if st.sidebar.button("🔄 Clear Cache & Reload"):
        st.cache_data.clear()
        st.rerun()

    # Simple string equality — no date type issues
    df_week = df[df["Week_Start"] == sel_week].copy()

    if view == "👥 Team Overview":
        render_team(df_week, sel_week_lbl)
    else:
        if sel_person is None:
            st.info("Select a person from the sidebar.")
        else:
            df_pw = df_week[df_week["Person"] == sel_person].copy()
            if len(df_pw) == 0:
                all_weeks = sorted(df[df["Person"] == sel_person]["Week_Start"].unique())
                st.warning(
                    f"No data for **{sel_person}** in week `{sel_week}`.\n\n"
                    f"Weeks found for this person: `{all_weeks}`"
                )
            else:
                render_individual(df_pw, sel_person)


if __name__ == "__main__":
    main()
