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
Common Lisp validation using SBLint (primary) and SBCL (secondary).
Provides machine-readable output for CI/CD integration.
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def run_sblint(target: str) -> List[Dict[str, Any]]:
    """
    Run SBLint for machine-readable linting.

    Args:
        target: File or directory path to lint

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        result = subprocess.run(
            ["sblint", target],
            capture_output=True,
            text=True,
            timeout=60
        )

        # SBLint outputs to stdout
        if result.stdout:
            errors.extend(parse_sblint_output(result.stdout))

        # Also check stderr for errors
        if result.stderr and "error" in result.stderr.lower():
            errors.extend(parse_sblint_output(result.stderr))

    except FileNotFoundError:
        errors.append({"error": "sblint not found (install via: ros install cxxxr/sblint)", "tool": "sblint"})
    except subprocess.TimeoutExpired:
        errors.append({"error": "sblint timed out", "file": target, "tool": "sblint"})
    except Exception as e:
        errors.append({"error": f"sblint error: {e}", "file": target, "tool": "sblint"})

    return errors


def parse_sblint_output(output: str) -> List[Dict[str, Any]]:
    """
    Parse SBLint's machine-readable output.
    Format: file:line:col: message

    Args:
        output: SBLint output

    Returns:
        List of parsed error dictionaries
    """
    errors = []
    # Pattern: file:line:col: message
    pattern = r'(.+?):(\d+):(\d+):\s*(.+)'

    for line in output.strip().split('\n'):
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            file, line_num, col, message = match.groups()

            # Determine severity from message content
            message_lower = message.lower()
            if any(word in message_lower for word in ["error", "undefined", "unbound"]):
                severity = "error"
            elif any(word in message_lower for word in ["warning", "style-warning"]):
                severity = "warning"
            else:
                severity = "info"

            errors.append({
                "file": file,
                "line": int(line_num),
                "col": int(col),
                "severity": severity,
                "message": message.strip(),
                "tool": "sblint"
            })

    return errors


def run_sbcl_compile_check(target: str) -> List[Dict[str, Any]]:
    """
    Run SBCL compiler for deep semantic validation.

    Args:
        target: File path to check

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        # Use --noinform to reduce noise, --disable-debugger to exit on error
        result = subprocess.run(
            [
                "sbcl",
                "--noinform",
                "--disable-debugger",
                "--load", target,
                "--quit"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # Parse SBCL's verbose error output
            error_output = result.stderr or result.stdout
            errors.extend(parse_sbcl_output(error_output, target))

    except FileNotFoundError:
        errors.append({"error": "sbcl not found", "tool": "sbcl"})
    except subprocess.TimeoutExpired:
        errors.append({"error": "sbcl timed out", "file": target, "tool": "sbcl"})
    except Exception as e:
        errors.append({"error": f"sbcl error: {e}", "file": target, "tool": "sbcl"})

    return errors


def parse_sbcl_output(output: str, filename: str) -> List[Dict[str, Any]]:
    """
    Parse SBCL's verbose error messages.

    SBCL errors can span multiple lines and have varying formats:
    - "READ error during COMPILE-FILE: ... Line: X, Column: Y"
    - "debugger invoked on a ... at character X"
    - "Warning: ..."

    Args:
        output: SBCL error output
        filename: Source file name

    Returns:
        List of parsed error dictionaries
    """
    errors = []

    # Pattern for "Line: X, Column: Y" format
    line_col_pattern = r'Line:\s*(\d+),\s*Column:\s*(\d+)'

    # Pattern for "at character X" format
    char_pattern = r'at character\s+(\d+)'

    # Split into logical error blocks
    current_error = None
    current_lines = []

    for line in output.split('\n'):
        # Check if this is a new error/warning
        if any(keyword in line for keyword in ["ERROR", "WARNING", "STYLE-WARNING", "NOTE", "debugger invoked"]):
            if current_error and current_lines:
                # Process previous error
                error_text = ' '.join(current_lines)
                error_dict = parse_sbcl_error_block(error_text, filename, current_error)
                if error_dict:
                    errors.append(error_dict)

            # Start new error
            if "ERROR" in line or "debugger invoked" in line:
                current_error = "error"
            elif "WARNING" in line:
                current_error = "warning"
            elif "STYLE-WARNING" in line:
                current_error = "info"
            else:
                current_error = "info"

            current_lines = [line]
        elif current_error:
            current_lines.append(line)

    # Process final error
    if current_error and current_lines:
        error_text = ' '.join(current_lines)
        error_dict = parse_sbcl_error_block(error_text, filename, current_error)
        if error_dict:
            errors.append(error_dict)

    return errors


def parse_sbcl_error_block(text: str, filename: str, severity: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single SBCL error block.

    Args:
        text: Error text
        filename: Source file
        severity: Error severity

    Returns:
        Error dictionary or None
    """
    line = 0
    col = 0

    # Try to extract line and column
    line_col_match = re.search(r'Line:\s*(\d+),\s*Column:\s*(\d+)', text)
    if line_col_match:
        line = int(line_col_match.group(1))
        col = int(line_col_match.group(2))

    # Extract the main error message
    message = text.strip()

    # Clean up common SBCL verbosity
    message = re.sub(r'debugger invoked on a [A-Z::-]+:\s*', '', message)
    message = re.sub(r'Type HELP for debugger help.*', '', message)
    message = message.strip()

    if not message:
        return None

    return {
        "file": filename,
        "line": line,
        "col": col,
        "severity": severity,
        "message": message[:500],  # Truncate very long messages
        "tool": "sbcl"
    }


def validate_common_lisp(target: str, use_sbcl: bool = True) -> Dict[str, Any]:
    """
    Validate Common Lisp code using SBLint and optionally SBCL.

    Args:
        target: File or directory path to validate
        use_sbcl: Whether to run SBCL for deep validation

    Returns:
        Validation results with findings and summary
    """
    result = {
        "target": target,
        "dialect": "common-lisp",
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": []
        }
    }

    # Run SBLint (primary)
    sblint_errors = run_sblint(target)

    for error in sblint_errors:
        if "error" in error and len(error) == 2:  # Tool error
            if "warnings" not in result:
                result["warnings"] = []
            result["warnings"].append(error["error"])
        else:
            result["findings"].append(error)
            if error["severity"] == "error":
                result["summary"]["total_errors"] += 1
            elif error["severity"] == "warning":
                result["summary"]["total_warnings"] += 1

    if "sblint not found" not in str(result.get("warnings", [])):
        result["summary"]["tools_used"].append("sblint")

    # Run SBCL (secondary) for single files
    if use_sbcl and Path(target).is_file():
        sbcl_errors = run_sbcl_compile_check(target)

        # Filter out duplicates
        existing_messages = {f["message"] for f in result["findings"]}

        for error in sbcl_errors:
            if "error" in error and len(error) == 2:  # Tool error
                if "warnings" not in result:
                    result["warnings"] = []
                result["warnings"].append(error["error"])
            elif error["message"] not in existing_messages:
                result["findings"].append(error)
                if error["severity"] == "error":
                    result["summary"]["total_errors"] += 1
                elif error["severity"] == "warning":
                    result["summary"]["total_warnings"] += 1

        if "sbcl not found" not in str(result.get("warnings", [])):
            result["summary"]["tools_used"].append("sbcl")

    # Sort findings
    result["findings"].sort(key=lambda x: (x["file"], x["line"], x["col"]))

    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_common_lisp.py <file-or-directory> [--no-sbcl]", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    use_sbcl = "--no-sbcl" not in sys.argv

    result = validate_common_lisp(target, use_sbcl=use_sbcl)

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
