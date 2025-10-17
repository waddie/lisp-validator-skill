#!/usr/bin/env python3
#
# Lisp Validator - Multi-dialect Lisp code validation tool
# Copyright (C) 2025  Tom Waddington
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Clojure validation using clj-kondo (primary) and joker (secondary).
Provides structured JSON output optimized for LLM integration.
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def run_clj_kondo(target: str) -> Dict[str, Any]:
    """
    Run clj-kondo with JSON output format.

    Args:
        target: File or directory path to lint

    Returns:
        Dict with findings and summary
    """
    try:
        result = subprocess.run(
            [
                "clj-kondo",
                "--lint", target,
                "--config", "{:output {:format :json}}"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout:
            return json.loads(result.stdout)
        return {"findings": [], "summary": {"error": 0, "warning": 0, "info": 0}}

    except FileNotFoundError:
        return {"error": "clj-kondo not found", "findings": [], "summary": {}}
    except subprocess.TimeoutExpired:
        return {"error": "clj-kondo timed out", "findings": [], "summary": {}}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse clj-kondo output: {e}", "findings": [], "summary": {}}
    except Exception as e:
        return {"error": f"clj-kondo error: {e}", "findings": [], "summary": {}}


def run_joker(target: str) -> List[Dict[str, Any]]:
    """
    Run joker linter for complementary validation.

    Args:
        target: File path to lint (joker processes one file at a time)

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        # Joker analyzes one file at a time
        target_path = Path(target)
        if target_path.is_file():
            files = [target_path]
        else:
            files = list(target_path.rglob("*.clj")) + list(target_path.rglob("*.cljs"))

        for file in files:
            result = subprocess.run(
                ["joker", "--lint", "--dialect", "clj", str(file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.stderr:
                errors.extend(parse_joker_output(result.stderr))

    except FileNotFoundError:
        errors.append({"error": "joker not found", "file": target, "tool": "joker"})
    except subprocess.TimeoutExpired:
        errors.append({"error": "joker timed out", "file": target, "tool": "joker"})
    except Exception as e:
        errors.append({"error": f"joker error: {e}", "file": target, "tool": "joker"})

    return errors


def parse_joker_output(output: str) -> List[Dict[str, Any]]:
    """
    Parse joker's text output into structured format.
    Format: <filename>:<line>:<column>: <issue type>: <message>

    Args:
        output: stderr output from joker

    Returns:
        List of parsed error dictionaries
    """
    errors = []
    # Pattern: filename:line:col: type: message
    pattern = r'(.+?):(\d+):(\d+):\s*(.+?):\s*(.+)'

    for line in output.strip().split('\n'):
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            filename, line_num, col, issue_type, message = match.groups()

            severity = "error" if "error" in issue_type.lower() else "warning"

            errors.append({
                "file": filename,
                "line": int(line_num),
                "col": int(col),
                "severity": severity,
                "message": message.strip(),
                "type": issue_type.strip(),
                "tool": "joker"
            })

    return errors


def normalize_clj_kondo_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize clj-kondo findings to unified format.

    Args:
        findings: List of findings from clj-kondo

    Returns:
        List of normalized error dictionaries
    """
    normalized = []

    for finding in findings:
        normalized.append({
            "file": finding.get("filename", "unknown"),
            "line": finding.get("row", 0),
            "col": finding.get("col", 0),
            "end_line": finding.get("end-row"),
            "end_col": finding.get("end-col"),
            "severity": finding.get("level", "error"),
            "message": finding.get("message", ""),
            "type": finding.get("type", "unknown"),
            "tool": "clj-kondo"
        })

    return normalized


def validate_clojure(target: str, use_joker: bool = True) -> Dict[str, Any]:
    """
    Validate Clojure code using clj-kondo and optionally joker.

    Args:
        target: File or directory path to validate
        use_joker: Whether to run joker as secondary validator

    Returns:
        Validation results with findings and summary
    """
    result = {
        "target": target,
        "dialect": "clojure",
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": []
        }
    }

    # Run clj-kondo (primary)
    kondo_result = run_clj_kondo(target)

    if "error" in kondo_result:
        result["warnings"] = [kondo_result["error"]]
    else:
        kondo_findings = normalize_clj_kondo_findings(kondo_result.get("findings", []))
        result["findings"].extend(kondo_findings)
        result["summary"]["tools_used"].append("clj-kondo")

        summary = kondo_result.get("summary", {})
        result["summary"]["total_errors"] += summary.get("error", 0)
        result["summary"]["total_warnings"] += summary.get("warning", 0)

    # Run joker (secondary)
    if use_joker:
        joker_errors = run_joker(target)

        # Filter out duplicates (same file:line:col)
        existing_locations = {
            (f["file"], f["line"], f["col"])
            for f in result["findings"]
        }

        for error in joker_errors:
            if "error" in error:
                if "warnings" not in result:
                    result["warnings"] = []
                result["warnings"].append(error["error"])
            else:
                location = (error["file"], error["line"], error["col"])
                if location not in existing_locations:
                    result["findings"].append(error)
                    if error["severity"] == "error":
                        result["summary"]["total_errors"] += 1
                    else:
                        result["summary"]["total_warnings"] += 1

        if "joker not found" not in str(result.get("warnings", [])):
            result["summary"]["tools_used"].append("joker")

    # Sort findings by file, then line, then column
    result["findings"].sort(key=lambda x: (x["file"], x["line"], x["col"]))

    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_clojure.py <file-or-directory> [--no-joker]", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    use_joker = "--no-joker" not in sys.argv

    result = validate_clojure(target, use_joker=use_joker)

    # Output JSON
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    if result["summary"]["total_errors"] > 0:
        sys.exit(3)
    elif result["summary"]["total_warnings"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
