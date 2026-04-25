def to_public_dict(value):
    return value.model_dump() if hasattr(value,"model_dump") else dict(value or {})
