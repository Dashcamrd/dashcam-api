"""
ACC mode helper — derives the tri-state ACC indicator from raw booleans.

Modes:
    green  — ACC ON  (شغاله)
    red    — ACC OFF, parking mode disabled (طافيه)
    orange — ACC OFF, parking mode enabled  (سكون)
"""

ACC_MODE_GREEN = "green"
ACC_MODE_RED = "red"
ACC_MODE_ORANGE = "orange"

ACC_MODE_LABELS = {
    ACC_MODE_GREEN: "شغاله",
    ACC_MODE_RED: "طافيه",
    ACC_MODE_ORANGE: "سكون",
}


def get_acc_mode(acc_on: bool, parking_mode: bool, is_online: bool = False) -> str:
    if acc_on:
        return ACC_MODE_GREEN
    # ACC off but device online → effectively in parking/sleep mode
    if parking_mode or is_online:
        return ACC_MODE_ORANGE
    return ACC_MODE_RED


def get_acc_mode_label(mode: str) -> str:
    return ACC_MODE_LABELS.get(mode, "")


def acc_mode_response(acc_on: bool, parking_mode: bool, is_online: bool = False) -> dict:
    """Return a dict fragment to merge into any API response."""
    mode = get_acc_mode(acc_on, parking_mode, is_online)
    return {
        "acc_mode": mode,
        "acc_mode_label": get_acc_mode_label(mode),
        "parking_mode": parking_mode or (not acc_on and is_online),
    }
