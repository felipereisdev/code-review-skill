"""Requirement: every named required check must keep severity=error."""


def accepted(config):
    for check in config.get("checks", []):
        if check.get("required") and check.get("severity") == "off":
            return False
    return True
