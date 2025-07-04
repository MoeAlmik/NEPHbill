import streamlit as st
from billing_functions import (
    consult_03_08A,
    consult_03_08CV,
    repeat_visit_03_03F,
    repeat_consultation_03_07B,
    followup_virtual_visit_03_03FV,
    prolonged_consult_addon_03_08I,
    optimal_billing_strategy
)

st.title("🩺 Alberta NEPH Billing Calculator")

# Visit Type Dropdown
visit_type = st.selectbox("Select Visit Type", [
    "New consult", "Repeat consult", "Follow up"
])

is_virtual = st.checkbox("Virtual Visit?", value=False)

# Time Entry as Units
units = st.number_input("Total time spent (in 15-minute units)", min_value=1, max_value=8, value=1)
duration = units * 15

# Map Visit Type to Code
if visit_type == "New consult":
    hsc_code = "03.08CV" if is_virtual else "03.08A"
elif visit_type == "Repeat consult":
    hsc_code = "03.07B"
elif visit_type == "Follow up":
    hsc_code = "03.03FV" if is_virtual else "03.03F"
else:
    hsc_code = None

# After-hours modifier options for 03.07B
if hsc_code == "03.07B":
    time_of_day = st.selectbox(
        "Time of Day (for after-hours SURC modifier)",
        ["None", "EV (Evening)", "WK (Weekend)", "NTAM (Night AM)", "NTPM (Night PM)"]
    )
    time_of_day_code = None if time_of_day == "None" else time_of_day.split()[0]
else:
    time_of_day_code = None

# Calculate Button
if st.button("Calculate Billing Amount"):
    result = optimal_billing_strategy(hsc_code, duration_minutes=duration, virtual=is_virtual)

    if hsc_code == "03.07B":
        base_fee_only = repeat_consultation_03_07B(
            complexity=result["modifiers_applied"][0] if result["modifiers_applied"] else None,
            virtual=is_virtual,
            time_of_day=time_of_day_code
        )

        # Compute addon fees separately
        addon_fee = 0
        for code in result["add_on_codes"]:
            if "03.08I" in code:
                units = int(code.split("(")[1].split()[0])
                addon_fee += prolonged_consult_addon_03_08I(units, is_virtual)

        result["total_fee"] = round(base_fee_only + addon_fee, 2)


    st.success(f"💵 Total Billable Amount: ${result['total_fee']:.2f}")
    st.write(f"📋 Visit Type: **{visit_type}** ({hsc_code})")
    if result["modifiers_applied"]:
        st.markdown("🧾 **Modifiers Applied:**")
        for i, mod in enumerate(result["modifiers_applied"], start=1):
            st.markdown(f"{i}: {mod}")
    if result["add_on_codes"]:
        st.markdown("➕ **Add-on Codes:**")
        for i, code in enumerate(result["add_on_codes"], start=1):
            st.markdown(f"{i}: {code}")

# -------------------------------------
# 📈 OPTIMIZATION SECTION
# -------------------------------------
st.header("📈 Optimize Clinic Billing")

clinic_duration_hours = st.number_input("Clinic duration (hours)", min_value=1, max_value=12, value=8)
total_patients = st.number_input("Total number of patients", min_value=1, value=20)

new_consults = st.number_input("Number of new consults", min_value=0, value=5)
repeat_consults = st.number_input("Number of repeat consults", min_value=0, value=5)
follow_ups = st.number_input("Number of follow-ups", min_value=0, value=10)

bulk_virtual = False  # You could add a checkbox to enable bulk virtual clinics if you want

# Optional: Time of day for all repeat consults
time_of_day_bulk = st.selectbox(
    "Time of Day for Repeat Consults (optional)",
    ["None", "EV (Evening)", "WK (Weekend)", "NTAM (Night AM)", "NTPM (Night PM)"]
)
time_of_day_code = None if time_of_day_bulk == "None" else time_of_day_bulk.split()[0]

if st.button("Optimize Billing"):
    if new_consults + repeat_consults + follow_ups != total_patients:
        st.error("Total visit counts must equal total number of patients.")
    else:
        total_minutes = clinic_duration_hours * 60
        avg_time_per_patient = total_minutes // total_patients

        revenue_new, revenue_repeat, revenue_follow = 0, 0, 0

        for _ in range(new_consults):
            r = optimal_billing_strategy("03.08A", duration_minutes=avg_time_per_patient, virtual=bulk_virtual)
            revenue_new += r["total_fee"]

        for _ in range(repeat_consults):
            r = optimal_billing_strategy("03.07B", duration_minutes=avg_time_per_patient, virtual=bulk_virtual)

            base_fee_only = repeat_consultation_03_07B(
                complexity=r["modifiers_applied"][0] if r["modifiers_applied"] else None,
                virtual=bulk_virtual,
                time_of_day=time_of_day_code
            )

            addon_fee = 0
            for code in r["add_on_codes"]:
                if "03.08I" in code:
                    units = int(code.split("(")[1].split()[0])
                    addon_fee += prolonged_consult_addon_03_08I(units, bulk_virtual)

            revenue_repeat += round(base_fee_only + addon_fee, 2)


        for _ in range(follow_ups):
            r = optimal_billing_strategy("03.03F", duration_minutes=avg_time_per_patient, virtual=bulk_virtual)
            revenue_follow += r["total_fee"]

        total_revenue = revenue_new + revenue_repeat + revenue_follow

        st.success(f"📊 Optimized Revenue: ${total_revenue:.2f}")
        st.markdown(f"- ⏱️ Average Time per Patient: **{avg_time_per_patient} minutes**")
        st.markdown(f"- 🧾 New Consults: ${revenue_new:.2f}")
        st.markdown(f"- 🔁 Repeat Consults: ${revenue_repeat:.2f}")
        st.markdown(f"- 📋 Follow-ups: ${revenue_follow:.2f}")
