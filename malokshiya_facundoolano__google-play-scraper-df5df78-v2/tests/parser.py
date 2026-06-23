"""Parse Mocha JSON reporter output into the standard test result format."""

import json
import sys
import re


def parse_mocha_json(stdout_file, stderr_file, output_file):
    with open(stdout_file, "r") as f:
        stdout = f.read()

    tests = []

    # Mocha JSON reporter may print non-JSON lines before the JSON object.
    # Find the JSON object by looking for the first '{' that starts a line.
    json_match = re.search(r"^\s*\{", stdout, re.MULTILINE)
    if json_match:
        json_str = stdout[json_match.start() :]
        # Find matching closing brace
        brace_count = 0
        end_idx = 0
        for i, c in enumerate(json_str):
            if c == "{":
                brace_count += 1
            elif c == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        json_str = json_str[:end_idx]

        try:
            data = json.loads(json_str)

            for test in data.get("passes", []):
                name = test.get("fullTitle", test.get("title", "unknown"))
                tests.append({"name": name, "status": "PASSED"})

            for test in data.get("failures", []):
                name = test.get("fullTitle", test.get("title", "unknown"))
                tests.append({"name": name, "status": "FAILED"})

            for test in data.get("pending", []):
                name = test.get("fullTitle", test.get("title", "unknown"))
                tests.append({"name": name, "status": "SKIPPED"})

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse mocha JSON output: {e}", file=sys.stderr)

    if not tests:
        # Fallback: if no JSON found, check stderr for error indicators
        with open(stderr_file, "r") as f:
            stderr = f.read()
        if "Error" in stderr or "Error" in stdout:
            tests.append({"name": "mocha_run", "status": "FAILED"})

    with open(output_file, "w") as f:
        json.dump({"tests": tests}, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <stdout_file> <stderr_file> <output_file>")
        sys.exit(1)
    parse_mocha_json(sys.argv[1], sys.argv[2], sys.argv[3])
