from adapter import normalize


def response(value):
    return {"name": normalize(value)}
