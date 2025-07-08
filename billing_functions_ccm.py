"""
Billing functions for Critical Care Medicine (CCM) Alberta.
Each function calculates the billable amount for a specific Health Service Code (HSC),
applying modifiers as appropriate.
"""

from typing import Optional, List, Tuple, Dict, Any

# --- Modifiers (expand as needed) ---
BMI_MODIFIERS = set(["BMINW", "BMIOB"])  # Example, expand as needed

# --- After-hours Modifier Fee Table ---
AFTER_HOURS_FEE = {
    "EV": 48.94,    # Weekday evening 17:00–22:00
    "WK": 48.94,    # Weekend/stat 07:00–22:00
    "NTPM": 117.41, # Night 22:00–24:00
    "NTAM": 117.41, # Night 00:00–07:00
}
TIME_MODIFIER_RATES = {
    "CMXC30": 31.59  # $31.59 per consult (not per unit!)
}

# --- Utility function to apply modifiers ---
def apply_modifiers(base_fee: float, modifiers: Optional[List[str]], *, units: int = 1) -> Tuple[float, List[str]]:
    mods = [str(m).upper() for m in (modifiers or [])]
    applied = []
    fee = base_fee

    # CRCM: Skill modifier (for consults: 03.08A)
    if 'CRCM' in mods and 'CRCM' not in applied:
        fee = 202.94
        applied.append('CRCM')
    # CMXC30: Per call (consults only)
    if 'CMXC30' in mods and 'CMXC30' not in applied:
        fee += 31.59
        applied.append('CMXC30')
    # BMI/complexity, if needed
    for mod in mods:
        if mod in BMI_MODIFIERS and mod not in applied:
            fee += base_fee * 0.25
            applied.append(mod)
    # After-hours modifier fee (EV, WK, NTPM, NTAM)
    for mod in mods:
        if mod in AFTER_HOURS_FEE and mod not in applied:
            fee += AFTER_HOURS_FEE[mod]
            applied.append(mod)
    # If units (per 15 min) matter for the code, multiply outside this function.
    return fee, applied

# ---- 03.08A - Comprehensive Consultation ----
def comprehensive_consult_03_08A(units: int = 1, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 80.0
    # Preserve all passed-in modifiers (for block code/after-hours) and always add CRCM, CMXC30 if not present
    mods = []
    if modifiers:
        mods += list(modifiers)
    if 'CRCM' not in [str(m).upper() for m in mods]:
        mods.append('CRCM')
    if 'CMXC30' not in [str(m).upper() for m in mods]:
        mods.append('CMXC30')
    # Always 2 units per consult (30min)
    units = 2
    fee_per_call, applied_mods = apply_modifiers(base_fee, mods, units=1)
    return {
        "HSC Code": "03.08A",
        "Description": "Comprehensive Consultation",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee_per_call, 2),
        "Units": units,
        "Calls": 1
    }

# ---- 03_07B - Repeat Consult/Transfer of Care ----
def repeat_consult_03_07B(units: int = 1, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 158.29  # Per call/case
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_call, applied_mods = apply_modifiers(base_fee, mods, units=1)
    # Always 1 units per repeat consult (30min)
    units = 1
    return {
        "HSC Code": "03.07B",
        "Description": "Repeat Consult / Transfer of Care",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee_per_call, 2),
        "Units": units,
        "Calls": 1,
        "Base Fee per Unit": base_fee
    }

# ---- 03.05A - ICU Visit (15 minutes per unit) ----
def icu_visit_03_05A(units: int = 1, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 58.32
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_unit, applied_mods = apply_modifiers(base_fee, mods)
    total_fee = fee_per_unit * units
    return {
        "HSC Code": "03.05A",
        "Description": "ICU Visit per 15 minutes",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(total_fee, 2),
        "Units": units,
        "Calls": units
    }

# ---- Callback Visit ----
CALLBACK_CODES = {
    "03.05N": {"description": "Callback - Weekday 0700–1700", "base_fee": 75.97},
    "03.05P": {"description": "Callback - Weekday Evening 1700–2200", "base_fee": 113.94},
    "03.05R": {"description": "Callback - Weekend/Stat 0700–2200", "base_fee": 113.94},
    "03.05QA": {"description": "Callback - Night 2200–2400", "base_fee": 151.92},
    "03.05QB": {"description": "Callback - Night 2400–0700", "base_fee": 151.92}
}

def callback_visit(code: str, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    code = code.upper()
    if code not in CALLBACK_CODES:
        raise ValueError(f"Unsupported callback code: {code}")
    info = CALLBACK_CODES[code]
    # Always include the code itself as a modifier
    mods = [code]
    if modifiers:
        # Don't double-add code
        mods += [m for m in modifiers if m.upper() != code]
    fee, applied_mods = apply_modifiers(info["base_fee"], mods)
    return {
        "HSC Code": code,
        "Description": info["description"],
        "Base Fee": info["base_fee"],
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 1,   # Always 1 unit per callback
        "Calls": 1
    }

# ---- 13.62A - Ventilatory Support (adds fee, not units) ----
def ventilation_13_62A(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 41.09
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee, applied_mods = apply_modifiers(base_fee, mods)
    return {
        "HSC Code": "13.62A",
        "Description": "Ventilation/CPAP/BiPAP (adds fee, not units)",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 0,
        "Calls": 1
    }

# ---- 10.04B - Emergency Intubation ----
def intubation_10_04B(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 106.61
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee, applied_mods = apply_modifiers(base_fee, mods)
    return {
        "HSC Code": "10.04B",
        "Description": "Emergency Intubation",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 0,
        "Calls": 1
    }

# ---- 50.91D - Radial Arterial Line ----
def radial_art_line_50_91D(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 54.54
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee, applied_mods = apply_modifiers(base_fee, mods)
    return {
        "HSC Code": "50.91D",
        "Description": "Radial Arterial Line",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 0,
        "Calls": 1
    }

# ---- 50.94D - Central Venous Catheter ----
def central_line_50_94D(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 67.83
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee, applied_mods = apply_modifiers(base_fee, mods)
    return {
        "HSC Code": "50.94D",
        "Description": "Central Venous Catheter",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 0,
        "Calls": 1
    }

# ---- Family Conference (03.05JC) ----
def family_conference_03_05JC(units: int = 1, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 58.32
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_unit, applied_mods = apply_modifiers(base_fee, mods, units=units)
    total_fee = fee_per_unit * units
    return {
        "HSC Code": "03.05JC",
        "Description": "Family Conference (15 min/unit)",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(total_fee, 2),
        "Units": units,
        "Calls": 1
    }

# ---- Team/Family Conference (03.05K, 30min = 2 units) ----
def team_family_conference_03_05K(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 58.32
    units = 2
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_unit, applied_mods = apply_modifiers(base_fee, mods, units=units)
    total_fee = fee_per_unit * units
    return {
        "HSC Code": "03.05K",
        "Description": "Team/Family Conference (30 mins)",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(total_fee, 2),
        "Units": units,
        "Calls": 1
    }

# ---- Multidisciplinary Conference (03.05JA, 1 unit) ----
def multidisciplinary_conference_03_05JA(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 44.92
    units = 1
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_unit, applied_mods = apply_modifiers(base_fee, mods, units=units)
    total_fee = fee_per_unit * units
    return {
        "HSC Code": "03.05JA",
        "Description": "Multidisciplinary Conference + ICU + Phone",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(total_fee, 2),
        "Units": units,
        "Calls": 1
    }

# ---- Resuscitation (Primary, 13.99E) ----
def resuscitation_primary_13_99E(units: int = 1, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 96.52
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_call, applied_mods = apply_modifiers(base_fee, mods, units=1)
    return {
        "HSC Code": "13.99E",
        "Description": "Resuscitation (Primary)",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee_per_call, 2),
        "Units": 1,  # If you want to count as 4 units per resusc (1hr), change to 4
        "Calls": 1
    }

# ---- Resuscitation (Second, 13.99EC) ----
def resuscitation_secondary_13_99EC(units: int = 1, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 87.70
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee_per_call, applied_mods = apply_modifiers(base_fee, mods, units=1)
    return {
        "HSC Code": "13.99EC",
        "Description": "Resuscitation (Secondary Physician)",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee_per_call, 2),
        "Units": 1,
        "Calls": 1
    }

# ---- Peripheral Vein Catheter (Ultrasound, 50.94E) ----
def peripheral_line_50_94E(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 68.20
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee, applied_mods = apply_modifiers(base_fee, mods)
    return {
        "HSC Code": "50.94E",
        "Description": "Peripheral Vein Catheter (Ultrasound-guided)",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 0,
        "Calls": 1
    }

# ---- Bronchoscopy (Nonoperative, 01.09) ----
def bronchoscopy_01_09(modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    base_fee = 132.62
    mods = []
    if modifiers:
        mods += list(modifiers)
    fee, applied_mods = apply_modifiers(base_fee, mods)
    return {
        "HSC Code": "01.09",
        "Description": "Nonoperative Bronchoscopy",
        "Base Fee": base_fee,
        "Modifiers Applied": [str(m).upper() for m in mods],
        "Total Fee": round(fee, 2),
        "Units": 0,
        "Calls": 1
    }
