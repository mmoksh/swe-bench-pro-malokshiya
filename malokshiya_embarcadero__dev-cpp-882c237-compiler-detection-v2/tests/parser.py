"""Parse pytest JUnit XML output into the standard test result format."""

import json
import sys
import xml.etree.ElementTree as ET


def parse_junit_xml(stdout_file, stderr_file, output_file):
    xml_path = "/tmp/pytest_results.xml"
    tests = []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for testcase in root.iter("testcase"):
            classname = testcase.get("classname", "")
            name = testcase.get("name", "unknown")
            full_name = f"{classname}::{name}" if classname else name

            if (
                testcase.find("failure") is not None
                or testcase.find("error") is not None
            ):
                status = "FAILED"
            elif testcase.find("skipped") is not None:
                status = "SKIPPED"
            else:
                status = "PASSED"

            tests.append({"name": full_name, "status": status})

    except (ET.ParseError, FileNotFoundError) as e:
        print(f"Warning: Failed to parse JUnit XML: {e}", file=sys.stderr)
        with open(stdout_file, "r") as f:
            stdout = f.read()
        with open(stderr_file, "r") as f:
            stderr = f.read()
        if "Error" in stderr or "Error" in stdout or "FAILED" in stdout:
            tests.append({"name": "pytest_run", "status": "FAILED"})

    with open(output_file, "w") as f:
        json.dump({"tests": tests}, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <stdout_file> <stderr_file> <output_file>")
        sys.exit(1)
    parse_junit_xml(sys.argv[1], sys.argv[2], sys.argv[3])
