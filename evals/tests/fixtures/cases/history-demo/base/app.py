def handle(value):
    if value is None:
        raise ValueError("value is required")
    return value.strip()
