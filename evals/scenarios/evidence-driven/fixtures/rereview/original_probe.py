"""Recorded reproduction from round 1, plus the accepted control."""
from gate import accepted


assert accepted("off") is False
assert accepted("disabled") is False
assert accepted("error") is True
