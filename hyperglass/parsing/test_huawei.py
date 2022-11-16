"""Test Huawei Parsing."""

# Standard Library
import sys
import json
from pathlib import Path

# Project
from hyperglass.log import log

# Local
from .huawei import parse_huawei

SAMPLE_FILES = (
    Path(__file__).parent.parent / "models" / "parsing" / "huawei.txt",
)


@log.catch
def run():
    """Run tests."""
    samples = ()
    if len(sys.argv) == 2:
        samples += (sys.argv[1],)
    else:
        for sample_file in SAMPLE_FILES:
            with sample_file.open("r") as file:
                samples += (file.read(),)

    for sample in samples:
        parsed = parse_huawei([sample])
        log.info(json.dumps(parsed, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    run()
