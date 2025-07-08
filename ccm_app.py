import streamlit as st
import streamlit_authenticator as stauth
import yaml

# Load the YAML config file
with open('config.yaml') as file:
    config = yaml.safe_load(file)

# Set up authentication
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# This draws the login form in your Streamlit app's sidebar or main area
name, authentication_status, username = authenticator.login('Login', 'main')

# Restrict access unless authenticated
if authentication_status:
    st.write(f"Welcome, {name}!")  # Place the rest of your app here!
elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")

import pandas as pd
import numpy as np
import collections.abc
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import plotly.express as px
from billing_functions_ccm import *

def consult_after_hours_modifier(callback_code, is_weekend):
    """
    Returns the after-hours SOMB modifier code and its explanation for consults.
    """
    if is_weekend:
        return "WK", "WK (Weekend/stat 07:00–22:00): +$48.94"
    elif callback_code == "03.05P":
        return "EV", "EV (Weekday evening 17:00–22:00): +$48.94"
    elif callback_code == "03.05QA":
        return "NTPM", "NTPM (Night 22:00–24:00): +$117.41"
    elif callback_code == "03.05QB":
        return "NTAM", "NTAM (Night 00:00–07:00): +$117.41"
    else:
        return None, "No after-hours modifier"

def extract_tb(mods, block_codes):
    # Accepts a list or string, returns the first matching block code found
    if isinstance(mods, str):
        import ast
        try:
            mods_eval = ast.literal_eval(mods)
            if isinstance(mods_eval, list):
                mods_list = [str(m).upper() for m in mods_eval]
            else:
                mods_list = [mods.upper()]
        except Exception:
            import re
            mods_list = re.findall(r"[\w.]+", mods.upper())
    elif isinstance(mods, list):
        mods_list = [str(m).upper() for m in mods]
    else:
        mods_list = [str(mods).upper()]
    for m in mods_list:
        if m in block_codes:
            return m
    return ""

# --- Sanitize and state management ---
def sanitize_entry(entry, source="Original"):
    def safe_convert(obj):
        if isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (list, tuple, set)):
            return [safe_convert(o) for o in obj]
        elif isinstance(obj, collections.abc.Mapping):
            return {str(safe_convert(k)): safe_convert(v) for k, v in obj.items()}
        else:
            return obj
    e = {str(safe_convert(k)): safe_convert(v) for k, v in entry.items()}
    e['Source'] = source
    if 'Calls' not in e:
        e['Calls'] = 1
    if 'Units' not in e:
        e['Units'] = 1
    return e

st.set_page_config(page_title="CCM Billing Optimizer", layout="wide")
st.title("🧾 Critical Care Billing Optimizer (Alberta)")

# --- Persistent state for reset ---
if 'entries' not in st.session_state:
    st.session_state.entries = []
if 'reset_flag' not in st.session_state:
    st.session_state.reset_flag = False

def reset_all():
    st.session_state.entries = []
    st.session_state.reset_flag = not st.session_state.reset_flag

# ---- Weekend logic ----
is_weekend = st.toggle("Is this a weekend or stat holiday?", value=False)
if is_weekend:
    st.info("All daytime and evening callbacks will use the weekend/stat code 03.05R.")

def get_block_limits_and_order(is_weekend):
    if is_weekend:
        return (
            {
                "03.05R": 15 * 4,    # 07:00–21:59, 60 units
                "03.05QA": 2 * 4,   # 22:00–23:59, 8 units
                "03.05QB": 7 * 4,   # 00:00–06:59, 28 units
            },
            ["03.05QB", "03.05QA", "03.05R"]  # NIGHT -> LATE EVE -> DAY
        )
    else:
        return (
            {
                "03.05N": 10 * 4,   # 40 units
                "03.05P": 5 * 4,    # 20 units
                "03.05QA": 2 * 4,   # 8 units
                "03.05QB": 7 * 4,   # 28 units
            },
            ["03.05QB", "03.05QA", "03.05P", "03.05N"]  # NIGHT -> LATE EVE -> EVE -> DAY
        )

TIME_BLOCKS = {
    "D: 2400–0659": "03.05QB",
    "A: 0700–1695": "03.05N",
    "B: 1700–2159": "03.05P",
    "C: 2200–2359": "03.05QA"
}

def get_callback_code(block_code, is_weekend):
    if is_weekend:
        if block_code in ["03.05N", "03.05P"]:
            return "03.05R"
        else:
            return block_code
    else:
        return block_code

AFTER_HOURS_ELIGIBLE_CODES = [
    "03.08A", 
    "03.07B", 
    "03.05A",
    "10.04B",
    "50.91D",
    "50.94D",
    "13.99E",
    "13.99EC",
    "50.94E",
    "01.09"
]  # Expand as needed

def get_modifiers_for_code(hsc_code, callback_code, is_weekend):
    """
    Returns a list of all applicable modifiers, including time block code and after-hours modifier.
    For consults, always add CRCM and CMXC30.
    """
    mods = []
    # After-hours modifier (e.g., WK, EV, NTPM, NTAM)
    modifier_code, _ = consult_after_hours_modifier(callback_code, is_weekend)
    # Always add the callback/time block code
    if callback_code:
        mods.append(callback_code)
    # Always add after-hours modifier if applicable
    if modifier_code and modifier_code != callback_code:
        mods.append(modifier_code)
    # For consults, always add CRCM and CMXC30 if not already present
    if hsc_code == "03.08A":
        if "CRCM" not in [m.upper() for m in mods]:
            mods.append("CRCM")
        if "CMXC30" not in [m.upper() for m in mods]:
            mods.append("CMXC30")
    return [m for m in mods if m]

# ---- User entry UI ----
def add_time_block_section(label, callback_code):
    with st.expander(f"⏱️ {label} Time Block", expanded=False):
        st.caption("Tip: Enter number of short (≤24 min) and long (≥25 min) return visits for optimal billing.")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("👥 Patient Encounters")
            consults = st.number_input(f"Consults ({label})", min_value=0, value=0, key=f"{label}_consults_{st.session_state.reset_flag}")
            repeat_consults = st.number_input(f"Repeat Consults ({label})", min_value=0, value=0, key=f"{label}_repeat_{st.session_state.reset_flag}")
            if callback_code == "03.05QB" and (consults > 0 or repeat_consults > 0):
                st.warning("**Remember to enter the number of calls (consults/repeats) manually for this block!**\n\nThe Optimizer does not add extra units to the overnight block (00:00–06:59), so only what you enter here will be billed.")
            
            icu_visits = st.number_input(f"ICU Visits ({label})", min_value=0, value=0, key=f"{label}_icu_{st.session_state.reset_flag}")
            short_returns = st.number_input(f"Short Return Visits ≤24 min ({label})", min_value=0, value=0, key=f"{label}_short_{st.session_state.reset_flag}")
            long_returns = st.number_input(f"Long Return Visits ≥25 min ({label})", min_value=0, value=0, key=f"{label}_long_{st.session_state.reset_flag}")
            vents = st.number_input(f"Vents/CPAP/BiPAP ({label})", min_value=0, value=0, key=f"{label}_vent_{st.session_state.reset_flag}")
            resus_units = st.number_input(f"Resuscitation Units ({label})", min_value=0, value=0, key=f"{label}_resus_{st.session_state.reset_flag}")
            callbacks = st.number_input(f"📞 Callbacks (extra, not auto-optimized) ({label})", min_value=0, value=0, key=f"{label}_callbacks_{st.session_state.reset_flag}")

        with col2:
            st.subheader("🛠️ Interventions & Meetings")
            intubations = st.number_input(f"Intubations ({label})", min_value=0, value=0, key=f"{label}_intubation_{st.session_state.reset_flag}")
            central_lines = st.number_input(f"Central Lines ({label})", min_value=0, value=0, key=f"{label}_central_{st.session_state.reset_flag}")
            art_lines = st.number_input(f"Arterial Lines ({label})", min_value=0, value=0, key=f"{label}_art_{st.session_state.reset_flag}")
            bronchs = st.number_input(f"Bronchoscopies ({label})", min_value=0, value=0, key=f"{label}_bronch_{st.session_state.reset_flag}")
            family_conf = st.number_input(f"Family Conferences ({label})", min_value=0, value=0, key=f"{label}_family_{st.session_state.reset_flag}")
            team_conf = st.number_input(f"Team Conferences ({label})", min_value=0, value=0, key=f"{label}_team_{st.session_state.reset_flag}")
            multi_conf = st.number_input(f"Multidisciplinary Conferences ({label})", min_value=0, value=0, key=f"{label}_multi_{st.session_state.reset_flag}")

        CALLBACK_MAX = {
            "03.05N": 5, "03.05P": 5, "03.05QA": 2, "03.05QB": 7, "03.05R": 5
        }
        cb_max = CALLBACK_MAX.get(callback_code, 0)
        n_callback = min(short_returns, cb_max)
        n_short_left = max(short_returns - cb_max, 0)
        n_long = long_returns

        # Populate st.session_state.entries
        st.session_state.entries.extend([
            *[{**comprehensive_consult_03_08A(modifiers=get_modifiers_for_code("03.08A", callback_code, is_weekend)), "Calls": 1} for _ in range(consults)],
            *[{**repeat_consult_03_07B(1, get_modifiers_for_code("03.07B", callback_code, is_weekend)), "Calls": 1} for _ in range(repeat_consults)],
            *[{**icu_visit_03_05A(1, get_modifiers_for_code("03.05A", callback_code, is_weekend)), "Calls": 1} for _ in range(icu_visits)],
            *[{**callback_visit(callback_code, get_modifiers_for_code(callback_code, callback_code, is_weekend)), "Calls": 1} for _ in range(n_callback)],
            *[{**icu_visit_03_05A(1, get_modifiers_for_code("03.05A", callback_code, is_weekend)), "Calls": 1} for _ in range(n_short_left)],
            *[{**icu_visit_03_05A(2, get_modifiers_for_code("03.05A", callback_code, is_weekend)), "Calls": 1} for _ in range(n_long)],
            *[{**ventilation_13_62A(get_modifiers_for_code("13.62A", callback_code, is_weekend)), "Calls": 1} for _ in range(vents)],
            *[{**resuscitation_primary_13_99E(1, get_modifiers_for_code("13.99E", callback_code, is_weekend)), "Calls": 1} for _ in range(resus_units)],
            *[{**callback_visit(callback_code, get_modifiers_for_code(callback_code, callback_code, is_weekend)), "Calls": 1} for _ in range(callbacks)],
            *[{**intubation_10_04B(get_modifiers_for_code("10.04B", callback_code, is_weekend)), "Calls": 1} for _ in range(intubations)],
            *[{**central_line_50_94D(get_modifiers_for_code("50.94D", callback_code, is_weekend)), "Calls": 1} for _ in range(central_lines)],
            *[{**radial_art_line_50_91D(get_modifiers_for_code("50.91D", callback_code, is_weekend)), "Calls": 1} for _ in range(art_lines)],
            *[{**bronchoscopy_01_09(get_modifiers_for_code("01.09", callback_code, is_weekend)), "Calls": 1} for _ in range(bronchs)],
            *[{**family_conference_03_05JC(1, get_modifiers_for_code("03.05JC", callback_code, is_weekend)), "Calls": 1} for _ in range(family_conf)],
            *[{**team_family_conference_03_05K(get_modifiers_for_code("03.05K", callback_code, is_weekend)), "Calls": 1} for _ in range(team_conf)],
            *[{**multidisciplinary_conference_03_05JA(get_modifiers_for_code("03.05JA", callback_code, is_weekend)), "Calls": 1} for _ in range(multi_conf)],
        ])

# ---- Top section UI and reset ----
st.markdown(
    '<style>div[data-testid="stSidebar"]{width: 320px !important;}</style>',
    unsafe_allow_html=True
)

st.button("🔄 Reset All Inputs", on_click=reset_all)

# ---- Generate all input sections ----
st.session_state.entries = []  # clear before collecting new input each run
for label, callback_code in TIME_BLOCKS.items():
    actual_callback_code = get_callback_code(callback_code, is_weekend)
    add_time_block_section(label, actual_callback_code)

# ---- Smart Summary with filler, warnings, unused units ----
def billing_summary(entries, total_hours, is_weekend):
    BLOCK_UNIT_LIMITS, BLOCK_ORDER = get_block_limits_and_order(is_weekend)
    df = pd.DataFrame([sanitize_entry(e) for e in entries])
    for col in df.columns:
        df[col] = df[col].astype(str)
    df['Units'] = pd.to_numeric(df.get("Units", 1), errors="coerce").fillna(1.0)
    df['Calls'] = pd.to_numeric(df.get("Calls", 1), errors="coerce").fillna(1.0)
    df['Total Fee'] = pd.to_numeric(df.get("Total Fee", 0), errors="coerce").fillna(0.0)

    # --- Time Block extraction for summary ---
    # (real extract_tb is now used here)
    df['Time Block'] = df['Modifiers Applied'].apply(lambda mods: extract_tb(mods, BLOCK_UNIT_LIMITS.keys()))

    # --- By block used/remaining/max ---
    summary_rows = []
    unused_units = 0
    total_units_allowed = int(total_hours * 4)
    units_used = df.groupby('Time Block')['Units'].sum().to_dict()

    block_warnings = []
    for block in BLOCK_ORDER:
        used = int(units_used.get(block, 0))
        cap = BLOCK_UNIT_LIMITS[block]
        fillable = max(cap - used, 0)
        percent = (used / cap * 100) if cap else 0
        block_warnings.append(
            f"**{block}**: {used}/{cap} units used"
            + (" (maxed out!)" if used >= cap else "")
        )
        summary_rows.append({
            "Block": block,
            "Units Used": used,
            "Max Units": cap,
            "Units Left": fillable,
            "Percent Used": f"{percent:.0f}%"
        })
    units_possible = sum(BLOCK_UNIT_LIMITS.values())
    if total_units_allowed > units_possible:
        unused_units = total_units_allowed - units_possible
        st.warning(f"⚠️ You have {unused_units} hours ({unused_units*15} minutes) of working time that cannot be billed due to time block limits.")

    st.markdown("#### ⏳ **Units Used per Block**")
    st.dataframe(pd.DataFrame(summary_rows))
    for warning in block_warnings:
        if "maxed out" in warning:
            st.error(warning)
        else:
            st.info(warning)
    st.write(df[['HSC Code', 'Description', 'Modifiers Applied', 'Units', 'Calls']])  # <-- Always show table
    return df, unused_units  # <-- ALWAYS returns!

# ---- Main UI logic for Calculate and Optimizer ----
with st.expander("🧮 Calculate (No Optimization)", expanded=False):
    if st.button("Calculate Billing"):
        total_hours = st.number_input("Total hours worked (for summary only, not optimization):", min_value=0.0, value=0.0, step=0.25, key="noopt_hours")
        df, _ = billing_summary(st.session_state.entries, total_hours, is_weekend)
        summary_df = df.groupby(['HSC Code', 'Description', 'Time Block']).agg(
            Calls=('Calls', 'sum'),
            Units=('Units', 'sum'),
            Total_Fee=('Total Fee', 'sum')
        ).reset_index()
        st.dataframe(summary_df)
        st.metric("Total Calls", int(summary_df['Calls'].sum()))
        st.metric("Total Units (15-min blocks)", int(summary_df['Units'].sum()))
        st.metric("Total Billing Amount", f"${summary_df['Total_Fee'].sum():,.2f}")

with st.expander("⚙️ Efficiency Optimizer", expanded=False):
    st.markdown("Maximize revenue by distributing available time efficiently across billed services.")
    total_hours = st.number_input("Enter total hours worked in this 24-hour period", min_value=0.0, value=0.0, step=0.25, key="opt_hours")
    run_opt = st.button("🚀 Run Optimizer")

    if run_opt:
        BLOCK_UNIT_LIMITS, _ = get_block_limits_and_order(is_weekend)

        # 1. Get a fresh copy of user-entered events
        df, unused_units = billing_summary(st.session_state.entries, total_hours, is_weekend)
        units_allowed = int(total_hours * 4)
        units_used_total = int(df['Units'].sum())
        units_to_allocate = max(units_allowed - units_used_total, 0)

        # 2. Chronological order for display
        CHRONOLOGICAL_BLOCK_ORDER = ["03.05QB", "03.05N", "03.05P", "03.05QA"]

        # 3. Filler allocation order (skip 03.05QB for optimizer)
        FILLER_BLOCK_ORDER = ["03.05QA", "03.05P", "03.05N"]


        # 4. Only fill time blocks where a patient was seen
        ACTIVE_HSC_FOR_FILLER = ["03.08A", "03.07B", "03.05A"]
        active_blocks = set(
            df[df['HSC Code'].isin(ACTIVE_HSC_FOR_FILLER)]['Time Block'].dropna().unique()
        )

        # 5. Current units used per block
        units_used_by_block = df.groupby('Time Block')['Units'].sum().to_dict()

        # 6. Filler logic
        fillers = []
        for code in FILLER_BLOCK_ORDER:
            if code not in active_blocks:
                continue  # Only fill blocks in which a patient was seen!
            block_cap = BLOCK_UNIT_LIMITS[code]
            already_used = int(units_used_by_block.get(code, 0))
            block_remaining = max(block_cap - already_used, 0)
            to_add = min(units_to_allocate, block_remaining)
            for _ in range(to_add):
                fillers.append(sanitize_entry(icu_visit_03_05A(1, [code]), "Optimizer"))
            units_to_allocate -= to_add
            units_used_by_block[code] = already_used + to_add
            if units_to_allocate <= 0:
                break

        # 7. Append filler visits to the DataFrame
        if fillers:
            filler_df = pd.DataFrame(fillers)
            for col in filler_df.columns:
                filler_df[col] = filler_df[col].astype(str)
            filler_df['Units'] = pd.to_numeric(filler_df.get("Units", 1), errors="coerce").fillna(1.0)
            filler_df['Calls'] = pd.to_numeric(filler_df.get("Calls", 1), errors="coerce").fillna(1.0)
            filler_df['Total Fee'] = pd.to_numeric(filler_df.get("Total Fee", 0), errors="coerce").fillna(0.0)
            filler_df['Time Block'] = filler_df['Modifiers Applied'].apply(
                lambda mods: extract_tb(mods, BLOCK_UNIT_LIMITS.keys())
            )
            df = pd.concat([df, filler_df], ignore_index=True)
        st.success("✅ Optimization complete!")

        # 8. Summarize in chronological block order for display
        summary_df = df.groupby(['HSC Code', 'Description', 'Time Block', 'Source']).agg(
            Calls=('Calls', 'sum'),
            Units=('Units', 'sum'),
            Total_Fee=('Total Fee', 'sum')
        ).reset_index()

        # Force categorical display for correct order
        summary_df['Time Block'] = pd.Categorical(
            summary_df['Time Block'], categories=CHRONOLOGICAL_BLOCK_ORDER, ordered=True
        )
        summary_df = summary_df.sort_values("Time Block")

        st.write(df[['HSC Code', 'Description', 'Units', 'Calls', 'Modifiers Applied', 'Time Block']])
        st.dataframe(summary_df)
        st.metric("Total Calls", int(summary_df['Calls'].sum()))
        st.metric("Total Units (15-min blocks)", int(summary_df['Units'].sum()))
        st.metric("Total Billing Amount", f"${summary_df['Total_Fee'].sum():,.2f}")

        # Export option
        csv = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download Results as CSV", data=csv, file_name="ccm_billing_summary.csv")

        # --- Visuals ---
        with st.expander("📈 Visual Summary: Billing Timeline", expanded=False):
            BLOCK_UNIT_LIMITS, BLOCK_ORDER = get_block_limits_and_order(is_weekend)
            billing_timeline = summary_df.groupby(["Time Block", "Source"]).agg(
                Total_Units=('Units', 'sum'),
                Total_Fee=('Total_Fee', 'sum')
            ).reset_index()
            billing_timeline['Time Block'] = pd.Categorical(
                billing_timeline['Time Block'], categories=CHRONOLOGICAL_BLOCK_ORDER, ordered=True
            )

            billing_timeline = billing_timeline.sort_values("Time Block")
            fig_units = px.bar(
                billing_timeline, x="Time Block", y="Total_Units", color="Source",
                title="Units Billed per Time Block (Original vs. Optimizer)",
                labels={"Total_Units": "Units"}, barmode="stack", text_auto=True
            )
            fig_fees = px.bar(
                billing_timeline, x="Time Block", y="Total_Fee", color="Source",
                title="Revenue per Time Block (Original vs. Optimizer)",
                labels={"Total_Fee": "Fee ($)"}, barmode="stack", text_auto=".2s"
            )
            st.plotly_chart(fig_units, use_container_width=True)
            st.plotly_chart(fig_fees, use_container_width=True)
            st.markdown("### 💰 Total Summary")
            st.metric("Total Units", int(billing_timeline['Total_Units'].sum()))
            st.metric("Total Fee", f"${billing_timeline['Total_Fee'].sum():,.2f}")
            if unused_units > 0:
                st.warning(f"⚠️ You have {unused_units} 15-min blocks of time not billable due to max units per block.")

        total_units_possible = sum(BLOCK_UNIT_LIMITS.values())
        actual_units_used = int(df['Units'].sum())
        efficiency_pct = 100.0 * actual_units_used / total_units_possible if total_units_possible else 0
        st.metric("Block Utilization Efficiency", f"{efficiency_pct:.1f}%")

        # --- Visuals ---
        with st.expander("📈 Visual Summary: Billing Timeline", expanded=False):
            billing_timeline = summary_df.groupby(["Time Block", "Source"]).agg(
                Total_Units=('Units', 'sum'),
                Total_Fee=('Total_Fee', 'sum')
            ).reset_index()
            billing_timeline['Time Block'] = pd.Categorical(
                billing_timeline['Time Block'], categories=BLOCK_ORDER, ordered=True
            )
            billing_timeline = billing_timeline.sort_values("Time Block")
            fig_units = px.bar(
                billing_timeline, x="Time Block", y="Total_Units", color="Source",
                title="Units Billed per Time Block (Original vs. Optimizer)",
                labels={"Total_Units": "Units"}, barmode="stack", text_auto=True
            )
            fig_fees = px.bar(
                billing_timeline, x="Time Block", y="Total_Fee", color="Source",
                title="Revenue per Time Block (Original vs. Optimizer)",
                labels={"Total_Fee": "Fee ($)"}, barmode="stack", text_auto=".2s"
            )
            st.plotly_chart(fig_units, use_container_width=True)
            st.plotly_chart(fig_fees, use_container_width=True)
            st.markdown("### 💰 Total Summary")
            st.metric("Total Units", int(billing_timeline['Total_Units'].sum()))
            st.metric("Total Fee", f"${billing_timeline['Total_Fee'].sum():,.2f}")
            if unused_units > 0:
                st.warning(f"⚠️ You have {unused_units} 15-min blocks of time not billable due to max units per block.")

        total_units_possible = sum(BLOCK_UNIT_LIMITS.values())
        actual_units_used = int(df['Units'].sum())
        efficiency_pct = 100.0 * actual_units_used / total_units_possible if total_units_possible else 0
        st.metric("Block Utilization Efficiency", f"{efficiency_pct:.1f}%")
