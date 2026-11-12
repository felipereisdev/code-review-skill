"""The changed integration was tested only against the hand-written fake."""
import json


def result_count(stdout):
    return len(json.loads(stdout)["results"])
