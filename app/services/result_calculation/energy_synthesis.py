"""
Energy Synthesis: fusion type from primary axis (mind) and chakra heart status.
"""


def compute_energy_synthesis(
    *,
    primary_axis: str,
    heart_status: str,
) -> dict[str, str | float]:
    """
    Compute Energy Synthesis from primary axis and heart chakra status.
    - mind_val: 100 if primary_axis == 'mind', else 0
    - heart_val: 100 if heart_status == 'Balanced', else 50
    - avg = (mind_val + heart_val) / 2
    - fusion: 'Clarity' if avg > 75 else 'Integration'
    """
    mind_val = 100 if (primary_axis or "").strip().lower() == "mind" else 0
    heart_val = 100 if (heart_status or "").strip() == "Balanced" else 50
    avg = (mind_val + heart_val) / 2
    fusion = "Clarity" if avg > 75 else "Integration"
    return {"fusion": fusion, "avg": avg}
