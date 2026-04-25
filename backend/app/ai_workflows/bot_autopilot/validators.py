def validate_no_unsafe_apply(readiness: dict) -> None:
    if readiness.get("status") == "blocked": raise ValueError("readiness blocked; cannot apply")
