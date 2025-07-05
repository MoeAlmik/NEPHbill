# --------------------------------------
# 🔐 Secure Alberta NEPH Billing App
# --------------------------------------

import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth

from billing_functions import (
    consult_03_08A,
    consult_03_08CV,
    repeat_visit_03_03F,
    repeat_consultation_03_07B,
    followup_virtual_visit_03_03FV,
    prolonged_consult_addon_03_08I,
    optimal_billing_strategy,
    redistribute_unbilled_units
)

# ---------------------------
# 🔒 User Authentication
# ---------------------------
names = ['Dr. Ali', 'Nurse Betty']
usernames = ['ali', 'betty']
passwords = ['pw1', 'pw2']  # ❗ Replace with strong, hashed passwords for deployment

hashed_pw = stauth.Hasher(passwords).generate()
authenticator = stauth.Authenticate(
    names, usernames, hashed_pw,
    'clinic_app', 'abcdef', cookie_expiry_days=1
)

name, auth_status, username = authenticator.login('Login', 'main')

if auth_status is False:
    st.error("Invalid credentials")
    st.stop()
elif auth_status is None:
    st.warning("Please enter your username and password")
    st.stop()
else:
    st.success(f"Welcome, {name} 👋")


# ---------------------------------
# 🩺 Individual Billing Calculator
# ---------------------------------
st.title("🩺 Alberta NEPH Billing Calculator")

visit_type = st.selectbox("Select Visit Type", ["New consult", "Repeat consult", "Follow up"])
is_virtual = st.checkbox("Virtual Visit?", value=False)
units = st.number_input("Total time spent (in 15-minute units)", min_value=1, max_value=8, value=1)
duration = units * 15

if visit_type == "New consult":
    hsc_code = "03.08CV" if is_virtual else "03.08A"
elif visit_type == "Repeat consult":
    hsc_code = "03.07B"
elif visit_type == "Follow up":
    hsc_code = "03.03FV" if is_virtual else "03.03F"
else:
    hsc_code = None

if hsc_code == "03.07B":
    time_of_day = st.selectbox(
        "Time of Day (for after-hours SURC modifier)",
        ["None", "EV (Evening)", "WK (Weekend)", "NTAM (Night AM)", "NTPM (Night PM)"]
    )
    time_of_day_code = None if time_of_day == "None" else time_of_day.split()[0]
else:
    time_of_day_code = None

if st.button("Calculate Billing Amount"):
    result = optimal_billing_strategy(
        hsc_code, duration_minutes=duration, virtual=is_virtual, time_of_day=time_of_day_code
    )

    if hsc_code == "03.07B":
        base_fee = repeat_consultation_03_07B(
            complexity=result["modifiers_applied"][0] if result["modifiers_applied"] else None,
            virtual=is_virtual,
            time_of_day=time_of_day_code
        )
        addon_fee = sum([
            prolonged_consult_addon_03_08I(int(code.split("(")[1].split()[0]), is_virtual)
            for code in result["add_on_codes"] if "03.08I" in code
        ])
        result["total_fee"] = round(base_fee + addon_fee, 2)

    st.success(f"💵 Total Billable Amount: ${result['total_fee']:.2f}")
    st.write(f"📋 Visit Type: **{visit_type}** ({hsc_code})")

    if result["modifiers_applied"]:
        st.markdown("🧾 **Modifiers Applied:**")
        for mod in result["modifiers_applied"]:
            st.markdown(f"- {mod}")

    if result["add_on_codes"]:
        st.markdown("➕ **Add-on Codes:**")
        for code in result["add_on_codes"]:
            st.markdown(f"- {code}")


# ---------------------------------------
# 📈 Optimization Section with RRNP
# ---------------------------------------
st.header("📈 Optimize Clinic Billing")

clinic_duration_hours = st.number_input("Clinic duration (hours)", min_value=1, max_value=12, value=8)
new_consults = st.number_input("Number of new consults", min_value=0, value=5)
repeat_consults = st.number_input("Number of repeat consults", min_value=0, value=5)
follow_ups = st.number_input("Number of follow-ups", min_value=0, value=10)

total_patients = new_consults + repeat_consults + follow_ups
st.markdown(f"👥 **Total Patients:** {total_patients}")

bulk_virtual = st.checkbox("Are all visits virtual?", value=False)
apply_rrnp = st.checkbox("Apply RRNP Uplift (+19.98%)", value=False)

time_of_day_bulk = st.selectbox(
    "Time of Day for Repeat Consults (optional)",
    ["None", "EV (Evening)", "WK (Weekend)", "NTAM (Night AM)", "NTPM (Night PM)"]
)
time_of_day_code = None if time_of_day_bulk == "None" else time_of_day_bulk.split()[0]

if st.button("Optimize Billing"):
    if total_patients == 0:
        st.error("Total patient count must be greater than 0.")
    else:
        total_minutes = clinic_duration_hours * 60
        avg_time = total_minutes // total_patients
        available_units = total_minutes // 15
        breakdown = []

        # New Consults
        for _ in range(new_consults):
            code = "03.08CV" if bulk_virtual else "03.08A"
            r = optimal_billing_strategy(code, duration_minutes=avg_time, virtual=bulk_virtual)
            fee = round(r["total_fee"] * 1.1998, 2) if apply_rrnp else r["total_fee"]
            breakdown.append({
                "Visit Type": "New Consult",
                "HSC Code": code,
                "Modifiers": ", ".join(r["modifiers_applied"]) or "-",
                "Add-ons": ", ".join(r["add_on_codes"]) or "-",
                "Fee ($)": fee
            })

        # Repeat Consults
        for _ in range(repeat_consults):
            r = optimal_billing_strategy("03.07B", duration_minutes=avg_time, virtual=bulk_virtual, time_of_day=time_of_day_code)
            base_fee = repeat_consultation_03_07B(
                complexity=r["modifiers_applied"][0] if r["modifiers_applied"] else None,
                virtual=bulk_virtual,
                time_of_day=time_of_day_code
            )
            addon_fee = sum([
                prolonged_consult_addon_03_08I(int(code.split("(")[1].split()[0]), bulk_virtual)
                for code in r["add_on_codes"] if "03.08I" in code
            ])
            total_fee = round(base_fee + addon_fee, 2)
            fee = round(total_fee * 1.1998, 2) if apply_rrnp else total_fee
            breakdown.append({
                "Visit Type": "Repeat Consult",
                "HSC Code": "03.07B",
                "Modifiers": ", ".join(r["modifiers_applied"]) or "-",
                "Add-ons": ", ".join(r["add_on_codes"]) or "-",
                "Fee ($)": fee
            })

        # Follow-ups
        for _ in range(follow_ups):
            code = "03.03FV" if bulk_virtual else "03.03F"
            r = optimal_billing_strategy(code, duration_minutes=avg_time, virtual=bulk_virtual)
            fee = round(r["total_fee"] * 1.1998, 2) if apply_rrnp else r["total_fee"]
            breakdown.append({
                "Visit Type": "Follow-up",
                "HSC Code": code,
                "Modifiers": ", ".join(r["modifiers_applied"]) or "-",
                "Add-ons": ", ".join(r["add_on_codes"]) or "-",
                "Fee ($)": fee
            })

        # Redistribute unused units
        breakdown = redistribute_unbilled_units(breakdown, available_units)

        # Summary Calculations
        total_revenue = sum(row["Fee ($)"] for row in breakdown)
        addon_units = sum([
            int(code.split("(")[1].split()[0])
            for row in breakdown
            for code in row["Add-ons"].split(", ")
            if "03.08I" in code
        ])
        base_units = new_consults * 2 + repeat_consults + follow_ups
        total_units_billed = base_units + addon_units
        unbilled_units = available_units - total_units_billed
        efficiency_pct = (total_units_billed / available_units) * 100

        # Results
        st.success(f"📊 Optimized Revenue: ${total_revenue:.2f}")
        if apply_rrnp:
            st.markdown("🔺 **RRNP Uplift Applied (19.98%)**")

        st.markdown(f"- ⏱️ Avg. Time per Patient: **{avg_time} mins**")
        st.markdown(f"- 🧾 New Consults: ${sum(row['Fee ($)'] for row in breakdown if row['Visit Type'] == 'New Consult'):.2f}")
        st.markdown(f"- 🔁 Repeat Consults: ${sum(row['Fee ($)'] for row in breakdown if row['Visit Type'] == 'Repeat Consult'):.2f}")
        st.markdown(f"- 📋 Follow-ups: ${sum(row['Fee ($)'] for row in breakdown if row['Visit Type'] == 'Follow-up'):.2f}")

        st.subheader("📋 Detailed Billing Breakdown")
        df = pd.DataFrame(breakdown)
        st.dataframe(df.style.format({"Fee ($)": "{:.2f}"}))

        st.markdown("---")
        st.subheader("🧮 Billing Unit Summary")
        st.markdown(f"- 📦 **Total Available Units**: {available_units}")
        st.markdown(f"- 💳 **Total Billed Units**: {total_units_billed}")
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 Base Units: {base_units}")
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 Add-on Units (03.08I): {addon_units}")
        st.markdown(f"- ⚠️ **Unbilled Units**: {unbilled_units}")
        st.markdown(f"- 📈 **Efficiency**: {efficiency_pct:.1f}%")
