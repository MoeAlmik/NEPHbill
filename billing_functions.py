def consult_03_08A(complexity: str = None) -> float:
    """
    Health Service Code: 03.08A
    Description: Comprehensive consultation - in office
    Base NEPH Fee: $211.62
    Allowed Complexity Modifiers:
        - 'CMXC30': +$31.59 (if ≥30 minutes spent on care)
    Conditions:
        - Must be referred.
        - Full history and specialty-appropriate physical required.
        - Consultation note to referring provider is mandatory.
        - May be billed once every 365 days per patient by same physician.
        - Cannot bill with surgical assist codes for same encounter.
    
    Parameters:
        complexity (str): 'CMXC30' to add complexity modifier if 30+ mins spent.
    
    Returns:
        float: Total billable amount.
    """
    base_fee = 211.62
    if complexity == "CMXC30":
        return base_fee + 31.59
    return base_fee

def consult_03_08CV(complexity: str = None) -> float:
    """
    Health Service Code: 03.08CV
    Description: Comprehensive consultation via telephone or secure videoconference
    Base NEPH Fee: $211.62
    Allowed Complexity Modifiers:
        - 'CMXC30': +$31.59 (if ≥30 minutes spent on care)
    Conditions:
        - Must be referred.
        - Personally rendered by the physician.
        - Start and stop times must be recorded.
        - Cannot claim surcharge or time premiums.
        - Cannot be claimed same day as in-person visit or other virtual codes.
        - One comprehensive consultation per 365 days per patient.
        - Patient must be located in Alberta or NWT.
    
    Parameters:
        complexity (str): 'CMXC30' to add complexity modifier if 30+ mins spent.
    
    Returns:
        float: Total billable amount.
    """
    base_fee = 211.62
    if complexity == "CMXC30":
        return base_fee + 31.59
    return base_fee

def repeat_visit_03_03F(complexity: str = None, virtual: bool = False) -> float:
    """
    Health Service Code: 03.03F
    Description: Repeat office visit or scheduled outpatient visit in a regional facility – referred cases only.
    Base NEPH Fee: $87.88

    Optional Modifiers:
        - complexity (str): Can be "CMXV15" (+$15.78) or "CMXV30" (+$31.59)
        - virtual (bool): If True, applies TELES modifier (+20%)

    Conditions:
        - May only claim one visit service per encounter.
        - May not claim extended time for indirect services.
        - Complexity modifier requires 15+ or 30+ minutes spent on same day.
        - Virtual modifier (TELES) only applies when service is done virtually.

    Returns:
        float: Total billable amount
    """
    base_fee = 87.88

    if virtual:
        base_fee *= 1.2  # TELES modifier: 120%

    if complexity == "CMXV15":
        base_fee += 15.78
    elif complexity == "CMXV30":
        base_fee += 31.59

    return round(base_fee, 2)

def repeat_consultation_03_07B(complexity: str = None, virtual: bool = False, time_of_day: str = None) -> float:
    """
    Health Service Code: 03.07B
    Description: Repeat consultation (referred only).
    Base NEPH Fee: $141.08

    Optional Modifiers:
        - complexity (str): Can be "CMXV15" or "CMXV30"
            Requires 15 or 30+ mins of same-day management for nephrologists
        - virtual (bool): If True, applies TELES modifier (120% of base)
        - time_of_day (str): One of ["EV", "WK", "NTAM", "NTPM"] for after-hours SURC modifier
            EV, WK: +$48.94
            NTAM, NTPM: +$117.41

    Conditions:
        - Referring provider must initiate repeat consult
        - Must document detailed record and meet GR 4.4.6
        - TELES only valid for secure video/telephone
        - CMXV modifiers valid for nephrology with qualifying time

    Returns:
        float: Total billable amount
    """
    base_fee = 141.08

    if virtual:
        base_fee *= 1.2  # TELES

    if complexity == "CMXV15":
        base_fee += 15.78
    elif complexity == "CMXV30":
        base_fee += 31.59

    if time_of_day == "EV" or time_of_day == "WK":
        base_fee += 48.94
    elif time_of_day == "NTAM" or time_of_day == "NTPM":
        base_fee += 117.41

    return round(base_fee, 2)

def followup_virtual_visit_03_03FV(complexity: str = None, duration_minutes: int = 15) -> float:
    """
    HSC: 03.03FV – Follow-up Virtual Visit (Telephone or Secure Video)
    Specialty: NEPH
    Base Fee: $82.00
    Modifiers:
        - complexity: "CMXV15" (+$15.78) if ≥15 mins,
                      "CMXV30" (+$31.59) if ≥30 mins
        - duration_minutes: used to determine which complexity modifier applies
        - TELE modifier is already built in (03.03FV is virtual)
    Returns total payable amount in dollars.
    """
    base_fee = 82.00

    if complexity == "CMXV15" and duration_minutes >= 15:
        base_fee += 15.78
    elif complexity == "CMXV30" and duration_minutes >= 30:
        base_fee += 31.59

    return round(base_fee, 2)

def prolonged_consult_addon_03_08I(calls: int = 1, virtual: bool = False) -> float:
    """
    HSC: 03.08I – Prolonged In-Office Consultation (per 15 mins or majority portion)
    Applies to: 03.04A, 03.04AZ, 03.04C, 03.07B, 03.08A, 03.08AZ
    Specialty: NEPH
    Base per unit: $54.81
    TELE modifier (virtual): +20%

    Parameters:
        calls (int): Number of 15-min units (1 to 6)
        virtual (bool): If True, applies TELE modifier (120%)

    Returns:
        float: Total fee for prolonged time addon
    """
    if not 1 <= calls <= 6:
        raise ValueError("Calls must be between 1 and 6")

    base_unit = 54.81
    total = base_unit * calls

    if virtual:
        total *= 1.2  # TELE modifier

    return round(total, 2)

def hsc_0303a():
    """
    Health Service Code: 03.03A
    Description: Limited assessment of a patient's condition - in office
    Base Rate (NEPH): $82.22
    Category: V Visit
    Eligible for: Nephrology (SKLL modifier NEPH)

    Notes:
    - Requires a history, focused physical exam, appropriate documentation, and advice to patient.
    - Includes ordering of diagnostic tests.
    - Cannot be claimed with 03.05JB during same encounter.

    Modifiers (Common for NEPH):
    - CMXV15: +$15.78 (≥15 min complex)
    - CMXV30: +$31.59 (≥30 min complex)
    - TELE: 120% if virtual (TELES modifier)
    - CMPX_CMGP: +$19.54 per additional complexity code (up to 10x)
    - Age Modifier (G75GP): Increases base to 120%

    Governing Rules Highlights:
    - Use for routine follow-up (in-office).
    - Can be billed for suture removal if physician did not originally place them.
    - Cannot combine with psychotherapy code in the same visit.
    - Code appears in GRs 1.31, 1.33, 4.2.2, 5.2.3, and 6.x as a standard visit item.

    Max Payout Example (NEPH, CMXV30, TELES):
    - Base: $82.22
    - +CMXV30: $31.59
    - TELE: 120% → (82.22 + 31.59) * 1.2 = $136.98

    """

    return {
        "code": "03.03A",
        "description": "Limited assessment (in office)",
        "base_rate": 82.22,
        "modifiers": {
            "CMXV15": 15.78,
            "CMXV30": 31.59,
            "TELE": "120% base multiplier",
            "CMPX_CMGP": 19.54,
            "AGE_G75GP": "120% base multiplier"
        },
        "notes": [
            "Includes focused H&P and orders",
            "Not to be billed with 03.05JB",
            "Part of 'in-office' service group"
        ],
        "category": "V Visit",
        "specialty_modifier": "NEPH"
    }

def hsc_13_99OA():
    """
    Health Service Code: 13.99OA
    Description: Weekly management of chronic dialysis (hemodialysis or peritoneal dialysis)
    Category: M Management
    Base rate: $50.84 (with NEPH skill modifier applied)
    Billing Notes:
        - Claimable once per patient per week regardless of modality (HD or PD).
        - May be claimed in addition to consultation or visit services if provided.
        - Includes all care coordination, monitoring, and indirect services for that week.
        - Typically submitted for each dialysis patient under active nephrology care.
    Fee Modifiers:
        - SKLL: NEPH → Replace base: $50.84
    Governing Rules:
        - May not be billed more than once per patient per 7-day period.
        - Not tied to specific visit encounters.
        - Supports chronic disease management billing workflows.
    """
    return {
        "code": "13.99OA",
        "description": "Weekly management of chronic dialysis (hemodialysis or peritoneal dialysis)",
        "category": "M Management",
        "skill_modifier": "NEPH",
        "base_rate_neph": 50.84,
        "frequency": "Once per patient per 7-day period",
        "additional_notes": [
            "Includes all indirect care and coordination.",
            "Can be claimed alongside consultations or visits if applicable.",
            "Useful for bundling into weekly revenue forecasting per dialysis patient."
        ]
    }

def optimal_billing_strategy(hsc_code: str, duration_minutes: int, virtual: bool = False, time_of_day: str = None) -> dict:
    """
    Returns the optimized billing for the given HSC code, time spent, and context.

    Parameters:
        hsc_code (str): The HSC code being billed.
        duration_minutes (int): Total time spent with the patient.
        virtual (bool): Whether the visit was virtual.
        time_of_day (str): SURC modifier if applicable (only for 03.07B).

    Returns:
        dict with base_code, modifiers_applied, add_on_codes, total_fee
    """
    base_fee = 0
    modifiers = []
    add_ons = []

    # NEW CONSULTS
    if hsc_code in ["03.08A", "03.08CV"]:
        complexity = "CMXC30" if duration_minutes >= 30 else None
        base_fee = consult_03_08A(complexity) if hsc_code == "03.08A" else consult_03_08CV(complexity)
        if complexity:
            modifiers.append(complexity)

        if duration_minutes > 30:
            extra_minutes = duration_minutes - 30
            i_units = extra_minutes // 15
            if i_units > 0:
                addon_fee = prolonged_consult_addon_03_08I(i_units, virtual)
                base_fee += addon_fee
                add_ons.append(f"03.08I ({i_units} unit{'s' if i_units > 1 else ''})")

    # REPEAT CONSULTS & FOLLOW-UPS
    elif hsc_code in ["03.07B", "03.03F", "03.03FV"]:
        complexity = "CMXV15" if duration_minutes >= 15 else None

        if hsc_code == "03.07B":
            base_fee = repeat_consultation_03_07B(complexity, virtual, time_of_day)
        elif hsc_code == "03.03F":
            base_fee = repeat_visit_03_03F(complexity, virtual)
        elif hsc_code == "03.03FV":
            base_fee = followup_virtual_visit_03_03FV(complexity, duration_minutes)

        if complexity:
            modifiers.append(complexity)

        if duration_minutes > 15:
            extra_minutes = duration_minutes - 15
            i_units = extra_minutes // 15
            if i_units > 0:
                addon_fee = prolonged_consult_addon_03_08I(i_units, virtual)
                base_fee += addon_fee
                add_ons.append(f"03.08I ({i_units} unit{'s' if i_units > 1 else ''})")

    return {
        "base_code": hsc_code,
        "modifiers_applied": modifiers,
        "add_on_codes": add_ons,
        "total_fee": round(base_fee, 2)
    }

def redistribute_unbilled_units(breakdown, available_units):
    """
    Distribute unused 15-min units as 03.08I add-ons fairly across eligible patients.
    """

    # Count already billed base units (2 per new consult, 1 for repeat/follow-up)
    base_units = (
        sum(2 for row in breakdown if row["Visit Type"] == "New Consult") +
        sum(1 for row in breakdown if row["Visit Type"] in ["Repeat Consult", "Follow-up"])
    )

    # Count existing add-on units
    addon_units = 0
    for row in breakdown:
        if "03.08I" in row["Add-ons"]:
            try:
                addon_units += int(row["Add-ons"].split("(")[1].split()[0])
            except:
                pass  # If there's any parsing issue, skip

    used_units = base_units + addon_units
    unbilled_units = available_units - used_units

    # Identify eligible rows (New or Repeat Consults)
    eligible_rows = [
        row for row in breakdown
        if row["Visit Type"] in ["New Consult", "Repeat Consult"]
    ]

    # Track current 03.08I counts per row
    for row in eligible_rows:
        if "03.08I" in row["Add-ons"]:
            current_units = int(row["Add-ons"].split("(")[1].split()[0])
        else:
            current_units = 0
        row["_current_addon_units"] = current_units  # temp key

    # Distribute 1 unit at a time across rows in round-robin fashion
    while unbilled_units > 0:
        updated = False
        for row in eligible_rows:
            if row["_current_addon_units"] < 6 and unbilled_units > 0:
                row["_current_addon_units"] += 1
                fee_incr = prolonged_consult_addon_03_08I(1, virtual=False)
                row["Fee ($)"] += fee_incr
                unbilled_units -= 1
                updated = True
        if not updated:
            break  # No one left to assign units to

    # Update Add-ons column to reflect redistributed units
    for row in eligible_rows:
        units = row["_current_addon_units"]
        if units > 0:
            row["Add-ons"] = f"03.08I ({units} unit{'s' if units > 1 else ''})"
        else:
            row["Add-ons"] = "-"

        # Clean up temporary field
        del row["_current_addon_units"]

    return breakdown

