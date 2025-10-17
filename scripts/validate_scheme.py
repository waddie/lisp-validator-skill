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
Racket/Scheme validation using raco tools (primary) with fallback to dialect-specific compilers.
raco tools work for both Racket and generic Scheme when available.
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def check_raco_available() -> bool:
    """Check if raco is available on the system."""
    try:
        subprocess.run(["raco", "version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_raco_expand(target: str) -> List[Dict[str, Any]]:
    """
    Run raco expand for safe syntax checking without execution.

    Args:
        target: File path to check

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        result = subprocess.run(
            ["raco", "expand", target],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0 and result.stderr:
            errors.extend(parse_raco_errors(result.stderr, target, "raco-expand"))

    except FileNotFoundError:
        errors.append({"error": "raco not found", "tool": "raco-expand"})
    except subprocess.TimeoutExpired:
        errors.append({"error": "raco expand timed out", "file": target, "tool": "raco-expand"})
    except Exception as e:
        errors.append({"error": f"raco expand error: {e}", "file": target, "tool": "raco-expand"})

    return errors


def run_raco_review(target: str) -> List[Dict[str, Any]]:
    """
    Run raco review for fast surface-level linting.

    Args:
        target: File or directory path to review

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        result = subprocess.run(
            ["raco", "review", target],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout:
            errors.extend(parse_raco_structured_output(result.stdout, "raco-review"))

    except FileNotFoundError:
        errors.append({"error": "raco review not installed (run: raco pkg install review)", "tool": "raco-review"})
    except subprocess.TimeoutExpired:
        errors.append({"error": "raco review timed out", "file": target, "tool": "raco-review"})
    except Exception as e:
        errors.append({"error": f"raco review error: {e}", "file": target, "tool": "raco-review"})

    return errors


def run_raco_warn(target: str) -> List[Dict[str, Any]]:
    """
    Run raco warn for comprehensive analysis.

    Args:
        target: File or directory path to check

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        result = subprocess.run(
            ["raco", "warn", target],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.stdout:
            errors.extend(parse_raco_warn_output(result.stdout, "raco-warn"))

    except FileNotFoundError:
        errors.append({"error": "raco warn not installed (run: raco pkg install syntax-warn)", "tool": "raco-warn"})
    except subprocess.TimeoutExpired:
        errors.append({"error": "raco warn timed out", "file": target, "tool": "raco-warn"})
    except Exception as e:
        errors.append({"error": f"raco warn error: {e}", "file": target, "tool": "raco-warn"})

    return errors


def parse_raco_errors(output: str, filename: str, tool: str) -> List[Dict[str, Any]]:
    """
    Parse raco error messages (typically from stderr).
    Format: file:line:column: message

    Args:
        output: Error output
        filename: Source file name
        tool: Tool name for tracking

    Returns:
        List of parsed error dictionaries
    """
    errors = []
    pattern = r'(.+?):(\d+):(\d+):\s*(.+)'

    for line in output.strip().split('\n'):
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            file, line_num, col, message = match.groups()
            errors.append({
                "file": file,
                "line": int(line_num),
                "col": int(col),
                "severity": "error",
                "message": message.strip(),
                "tool": tool
            })
        elif "error" in line.lower() or "unbound" in line.lower():
            # Catch unstructured error messages
            errors.append({
                "file": filename,
                "line": 0,
                "col": 0,
                "severity": "error",
                "message": line.strip(),
                "tool": tool
            })

    return errors


def parse_raco_structured_output(output: str, tool: str) -> List[Dict[str, Any]]:
    """
    Parse raco review/warn structured output.
    Format: filename:line:col:level:message

    Args:
        output: Tool output
        tool: Tool name for tracking

    Returns:
        List of parsed error dictionaries
    """
    errors = []
    # Pattern: filename:line:col:level:message
    pattern = r'(.+?):(\d+):(\d+):(error|warning|info):\s*(.+)'

    for line in output.strip().split('\n'):
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            file, line_num, col, level, message = match.groups()
            errors.append({
                "file": file,
                "line": int(line_num),
                "col": int(col),
                "severity": level,
                "message": message.strip(),
                "tool": tool
            })

    return errors


def parse_raco_warn_output(output: str, tool: str) -> List[Dict[str, Any]]:
    """
    Parse raco warn output with suggestions.
    Format: file:line:col:level: message (code) suggestion: action

    Args:
        output: raco warn output
        tool: Tool name for tracking

    Returns:
        List of parsed error dictionaries
    """
    errors = []
    # More complex pattern with optional suggestion
    pattern = r'(.+?):(\d+):(\d+):(warning|error|info):\s*(.+?)(?:\s+suggestion:\s*(.+))?$'

    for line in output.strip().split('\n'):
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            file, line_num, col, level, message, suggestion = match.groups()

            error_dict = {
                "file": file,
                "line": int(line_num),
                "col": int(col),
                "severity": level,
                "message": message.strip(),
                "tool": tool
            }

            if suggestion:
                error_dict["suggestion"] = suggestion.strip()

            errors.append(error_dict)

    return errors


def run_fallback_scheme_validator(target: str, dialect: str = "guile") -> List[Dict[str, Any]]:
    """
    Fallback to dialect-specific Scheme validators when raco is unavailable.

    Args:
        target: File path to validate
        dialect: Scheme dialect (guile, chez, chicken, mit)

    Returns:
        List of error dictionaries
    """
    errors = []

    validators = {
        "guile": ["guile", "-c", f'(load "{target}")'],
        "chez": ["scheme", "--script", target],
        "chicken": ["csc", "-A", target],
        "mit": ["mit-scheme", "--load", target]
    }

    if dialect not in validators:
        return [{"error": f"Unknown Scheme dialect: {dialect}"}]

    try:
        result = subprocess.run(
            validators[dialect],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            # Different dialects have different error formats
            error_output = result.stderr or result.stdout

            # Generic parsing for unstructured Scheme errors
            for line in error_output.split('\n'):
                if any(keyword in line.lower() for keyword in ["error", "unbound", "undefined", "syntax"]):
                    errors.append({
                        "file": target,
                        "line": 0,
                        "col": 0,
                        "severity": "error",
                        "message": line.strip(),
                        "tool": f"scheme-{dialect}"
                    })

    except FileNotFoundError:
        errors.append({"error": f"{dialect} not found", "tool": f"scheme-{dialect}"})
    except subprocess.TimeoutExpired:
        errors.append({"error": f"{dialect} timed out", "file": target, "tool": f"scheme-{dialect}"})
    except Exception as e:
        errors.append({"error": f"{dialect} error: {e}", "file": target, "tool": f"scheme-{dialect}"})

    return errors


def validate_scheme(target: str, use_raco: bool = True, scheme_dialect: str = "guile") -> Dict[str, Any]:
    """
    Validate Racket/Scheme code using raco tools or dialect-specific validators.

    Args:
        target: File or directory path to validate
        use_raco: Whether to use raco tools (if available)
        scheme_dialect: Fallback Scheme dialect if raco unavailable

    Returns:
        Validation results with findings and summary
    """
    result = {
        "target": target,
        "dialect": "racket/scheme",
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": []
        }
    }

    raco_available = check_raco_available() if use_raco else False

    if raco_available:
        # Use raco tools (works for Racket and generic Scheme)
        # Fast check first
        expand_errors = run_raco_expand(target)
        result["findings"].extend([e for e in expand_errors if "error" not in e])
        result["summary"]["tools_used"].append("raco-expand")

        # Surface lint
        review_errors = run_raco_review(target)
        result["findings"].extend([e for e in review_errors if "error" not in e])
        if review_errors and "not installed" not in str(review_errors[0]):
            result["summary"]["tools_used"].append("raco-review")

        # Deep analysis
        warn_errors = run_raco_warn(target)
        result["findings"].extend([e for e in warn_errors if "error" not in e])
        if warn_errors and "not installed" not in str(warn_errors[0]):
            result["summary"]["tools_used"].append("raco-warn")

    else:
        # Fallback to dialect-specific validators
        fallback_errors = run_fallback_scheme_validator(target, scheme_dialect)
        result["findings"].extend([e for e in fallback_errors if "error" not in e])
        result["summary"]["tools_used"].append(f"scheme-{scheme_dialect}")

    # Count errors and warnings
    for finding in result["findings"]:
        if finding.get("severity") == "error":
            result["summary"]["total_errors"] += 1
        elif finding.get("severity") == "warning":
            result["summary"]["total_warnings"] += 1

    # Sort findings
    result["findings"].sort(key=lambda x: (x.get("file", ""), x.get("line", 0), x.get("col", 0)))

    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_scheme.py <file-or-directory> [--no-raco] [--dialect guile|chez|chicken|mit]", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    use_raco = "--no-raco" not in sys.argv

    # Parse dialect option
    scheme_dialect = "guile"
    for i, arg in enumerate(sys.argv):
        if arg == "--dialect" and i + 1 < len(sys.argv):
            scheme_dialect = sys.argv[i + 1]

    result = validate_scheme(target, use_raco=use_raco, scheme_dialect=scheme_dialect)

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
