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
Main orchestrator for Lisp validation across all dialects.
Auto-detects dialect and routes to appropriate validators.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import shared types and constants
try:
    from validation_types import (
        ValidationResult, Finding, ValidationSummary,
        DIALECT_DETECTION_BYTES, EXIT_SUCCESS, EXIT_WARNINGS, EXIT_ERRORS,
        DIALECT_CLOJURE, DIALECT_RACKET, DIALECT_SCHEME,
        DIALECT_COMMON_LISP, DIALECT_ELISP, DIALECT_UNKNOWN
    )
except ImportError:
    # Handle when running as script
    import importlib.util
    script_dir = Path(__file__).parent
    spec = importlib.util.spec_from_file_location("validation_types", script_dir / "validation_types.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ValidationResult = module.ValidationResult
    Finding = module.Finding
    ValidationSummary = module.ValidationSummary
    DIALECT_DETECTION_BYTES = module.DIALECT_DETECTION_BYTES
    EXIT_SUCCESS = module.EXIT_SUCCESS
    EXIT_WARNINGS = module.EXIT_WARNINGS
    EXIT_ERRORS = module.EXIT_ERRORS
    DIALECT_CLOJURE = module.DIALECT_CLOJURE
    DIALECT_RACKET = module.DIALECT_RACKET
    DIALECT_SCHEME = module.DIALECT_SCHEME
    DIALECT_COMMON_LISP = module.DIALECT_COMMON_LISP
    DIALECT_ELISP = module.DIALECT_ELISP
    DIALECT_UNKNOWN = module.DIALECT_UNKNOWN

# Import dialect-specific validators
try:
    from validate_clojure import validate_clojure
    from validate_scheme import validate_scheme
    from validate_common_lisp import validate_common_lisp
    from validate_tree_sitter import validate_tree_sitter
except ImportError:
    # Handle when running as script
    import importlib.util
    import os

    script_dir = Path(__file__).parent

    def load_module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    clojure_mod = load_module("validate_clojure", script_dir / "validate_clojure.py")
    scheme_mod = load_module("validate_scheme", script_dir / "validate_scheme.py")
    commonlisp_mod = load_module("validate_common_lisp", script_dir / "validate_common_lisp.py")
    treesitter_mod = load_module("validate_tree_sitter", script_dir / "validate_tree_sitter.py")

    validate_clojure = clojure_mod.validate_clojure
    validate_scheme = scheme_mod.validate_scheme
    validate_common_lisp = commonlisp_mod.validate_common_lisp
    validate_tree_sitter = treesitter_mod.validate_tree_sitter


def detect_dialect_from_extension(file_path: str) -> Optional[str]:
    """
    Detect Lisp dialect from file extension.

    Args:
        file_path: Path to source file

    Returns:
        Dialect name or None
    """
    ext = Path(file_path).suffix.lower()

    extension_map = {
        ".clj": DIALECT_CLOJURE,
        ".cljs": DIALECT_CLOJURE,
        ".cljc": DIALECT_CLOJURE,
        ".edn": DIALECT_CLOJURE,
        ".rkt": DIALECT_RACKET,
        ".scm": DIALECT_SCHEME,
        ".ss": DIALECT_SCHEME,
        ".lisp": DIALECT_COMMON_LISP,
        ".cl": DIALECT_COMMON_LISP,
        ".asd": DIALECT_COMMON_LISP,
        ".el": DIALECT_ELISP
    }

    return extension_map.get(ext)


def detect_dialect_from_content(content: str) -> Optional[str]:
    """
    Detect Lisp dialect from file content using heuristics.

    Args:
        content: File content

    Returns:
        Dialect name or None
    """
    # Clojure indicators
    if re.search(r'^\s*\(ns\s+', content, re.MULTILINE):
        return DIALECT_CLOJURE

    if re.search(r'\[.*:as\s+', content) or '::' in content:
        return DIALECT_CLOJURE

    # Racket indicators
    if re.search(r'^\s*#lang\s+racket', content, re.MULTILINE):
        return DIALECT_RACKET

    if re.search(r'^\s*\(module\s+', content, re.MULTILINE):
        return DIALECT_RACKET

    # Common Lisp indicators
    if re.search(r'^\s*\(defpackage\s+', content, re.MULTILINE):
        return DIALECT_COMMON_LISP

    if re.search(r'^\s*\(in-package\s+', content, re.MULTILINE):
        return DIALECT_COMMON_LISP

    if re.search(r'^\s*\(defsystem\s+', content, re.MULTILINE):
        return DIALECT_COMMON_LISP

    # Scheme indicators (less distinctive)
    if re.search(r'^\s*\(define-module\s+', content, re.MULTILINE):
        return DIALECT_SCHEME

    return None


def detect_dialect(target: str) -> str:
    """
    Auto-detect Lisp dialect from file or directory.

    Args:
        target: File or directory path

    Returns:
        Detected dialect or "unknown"
    """
    path = Path(target)

    # For directories, check first file
    if path.is_dir():
        for ext in [".clj", ".lisp", ".rkt", ".scm"]:
            files = list(path.rglob(f"*{ext}"))
            if files:
                target = str(files[0])
                path = Path(target)
                break

    # Try extension first
    if path.is_file():
        dialect = detect_dialect_from_extension(str(path))
        if dialect:
            return dialect

        # Try content analysis
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(DIALECT_DETECTION_BYTES)
                dialect = detect_dialect_from_content(content)
                if dialect:
                    return dialect
        except Exception:
            pass

    return DIALECT_UNKNOWN


def validate(target: str, dialect: Optional[str] = None, use_tree_sitter: bool = False) -> Dict[str, Any]:
    """
    Main validation entry point.

    Args:
        target: File or directory to validate
        dialect: Force specific dialect (auto-detect if None)
        use_tree_sitter: Force tree-sitter validation (for incomplete code)

    Returns:
        Unified validation results
    """
    # Validate target path exists
    target_path = Path(target)
    if not target_path.exists():
        return {
            "error": f"Target not found: {target}",
            "target": target,
            "dialect": DIALECT_UNKNOWN,
            "findings": [],
            "summary": {
                "total_errors": 0,
                "total_warnings": 0,
                "tools_used": []
            }
        }

    # Auto-detect dialect if not specified
    if not dialect:
        dialect = detect_dialect(target)

    result = {
        "target": target,
        "detected_dialect": dialect,
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": []
        }
    }

    # Route to appropriate validator
    if use_tree_sitter:
        # Force tree-sitter for incomplete code
        validator_result = validate_tree_sitter(target)
    elif dialect == DIALECT_CLOJURE:
        validator_result = validate_clojure(target)
    elif dialect in [DIALECT_RACKET, DIALECT_SCHEME]:
        validator_result = validate_scheme(target)
    elif dialect == DIALECT_COMMON_LISP:
        validator_result = validate_common_lisp(target)
    elif dialect == DIALECT_ELISP:
        # Elisp: use tree-sitter as primary option
        validator_result = validate_tree_sitter(target)
    elif dialect == DIALECT_UNKNOWN:
        # Fallback: try tree-sitter
        validator_result = validate_tree_sitter(target)
        if "warnings" not in result:
            result["warnings"] = []
        result["warnings"].append("Could not auto-detect dialect, using tree-sitter fallback")
    else:
        return {
            "error": f"Unsupported dialect: {dialect}",
            "target": target
        }

    # Merge results
    result["findings"] = validator_result.get("findings", [])
    result["summary"] = validator_result.get("summary", {})

    if "warnings" in validator_result:
        if "warnings" not in result:
            result["warnings"] = []
        result["warnings"].extend(validator_result["warnings"])

    return result


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    Format validation results.

    Args:
        result: Validation results
        output_format: Output format (json, text, summary)

    Returns:
        Formatted string
    """
    if output_format == "json":
        return json.dumps(result, indent=2)

    elif output_format == "text":
        lines = []
        lines.append(f"Target: {result['target']}")
        lines.append(f"Dialect: {result['detected_dialect']}")
        lines.append("")

        if result["findings"]:
            lines.append("Findings:")
            for finding in result["findings"]:
                location = f"{finding['file']}:{finding['line']}:{finding['col']}"
                severity = finding['severity'].upper()
                message = finding['message']
                lines.append(f"  [{severity}] {location}: {message}")
        else:
            lines.append("No issues found!")

        lines.append("")
        summary = result["summary"]
        lines.append(f"Summary: {summary['total_errors']} errors, {summary['total_warnings']} warnings")
        lines.append(f"Tools used: {', '.join(summary['tools_used'])}")

        return "\n".join(lines)

    elif output_format == "summary":
        summary = result["summary"]
        tools = ', '.join(summary['tools_used'])
        return f"{summary['total_errors']} errors, {summary['total_warnings']} warnings ({tools})"

    else:
        return json.dumps(result, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate.py <file-or-directory> [options]", file=sys.stderr)
        print("\nOptions:", file=sys.stderr)
        print("  --dialect <dialect>       Force specific dialect (clojure|racket|scheme|common-lisp|elisp)", file=sys.stderr)
        print("  --tree-sitter             Force tree-sitter validation (for incomplete code)", file=sys.stderr)
        print("  --format <format>         Output format (json|text|summary) [default: json]", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  validate.py src/", file=sys.stderr)
        print("  validate.py file.clj --format text", file=sys.stderr)
        print("  validate.py incomplete.lisp --tree-sitter", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]

    # Parse options
    dialect = None
    use_tree_sitter = False
    output_format = "json"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--dialect" and i + 1 < len(sys.argv):
            dialect = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--tree-sitter":
            use_tree_sitter = True
            i += 1
        elif sys.argv[i] == "--format" and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # Validate
    result = validate(target, dialect=dialect, use_tree_sitter=use_tree_sitter)

    # Output
    print(format_output(result, output_format))

    # Exit with appropriate code
    summary = result.get("summary", {})
    if summary.get("total_errors", 0) > 0:
        sys.exit(EXIT_ERRORS)
    elif summary.get("total_warnings", 0) > 0:
        sys.exit(EXIT_WARNINGS)
    else:
        sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
