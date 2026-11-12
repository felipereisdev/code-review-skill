"""The author's current suite alone misses the reopened alias."""
from gate import accepted


assert accepted("off") is False
assert accepted("error") is True
