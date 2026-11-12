"""A tiny executable external tool; its empty encoding is deliberately irregular."""
import json
import sys


if __name__ == "__main__":
    findings = sys.argv[1:]
    print(json.dumps({"results": findings} if findings else []))
