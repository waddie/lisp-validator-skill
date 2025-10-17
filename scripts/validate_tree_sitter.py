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
Tree-sitter based validation for incomplete Lisp code.
Critical for LLM workflows where code may be partially generated.

Handles incomplete expressions that traditional readers would reject.
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def check_tree_sitter_available() -> bool:
    """Check if tree-sitter CLI is available."""
    try:
        subprocess.run(["tree-sitter", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def detect_grammar(file_path: str) -> Optional[str]:
    """
    Detect appropriate tree-sitter grammar from file extension.

    Args:
        file_path: Path to source file

    Returns:
        Grammar name or None if unsupported
    """
    ext = Path(file_path).suffix.lower()

    grammar_map = {
        ".clj": "clojure",
        ".cljs": "clojure",
        ".cljc": "clojure",
        ".lisp": "commonlisp",
        ".cl": "commonlisp",
        ".asd": "commonlisp",
        ".el": "elisp",
        ".rkt": "racket",  # if tree-sitter-racket available
        ".scm": "scheme"   # generic
    }

    return grammar_map.get(ext)


def run_tree_sitter_parse(file_path: str) -> Dict[str, Any]:
    """
    Run tree-sitter parse and extract errors.

    Args:
        file_path: Path to source file

    Returns:
        Parse result with tree and errors
    """
    try:
        result = subprocess.run(
            ["tree-sitter", "parse", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "output": result.stdout,
            "success": result.returncode == 0,
            "tree": result.stdout
        }

    except FileNotFoundError:
        return {"error": "tree-sitter CLI not found (install: npm install -g tree-sitter-cli@0.19.3)"}
    except subprocess.TimeoutExpired:
        return {"error": "tree-sitter parse timed out"}
    except Exception as e:
        return {"error": f"tree-sitter error: {e}"}


def parse_tree_sitter_output(output: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Extract ERROR nodes from tree-sitter parse tree output.

    Tree-sitter marks unparseable sections as ERROR nodes in the parse tree.

    Args:
        output: tree-sitter parse output
        file_path: Source file path

    Returns:
        List of error dictionaries
    """
    errors = []

    # Pattern for ERROR nodes: ERROR [row, col] - [row, col]
    error_pattern = r'ERROR\s+\[(\d+),\s*(\d+)\]\s*-\s*\[(\d+),\s*(\d+)\]'

    for match in re.finditer(error_pattern, output):
        start_row, start_col, end_row, end_col = match.groups()

        errors.append({
            "file": file_path,
            "line": int(start_row) + 1,  # tree-sitter uses 0-based indexing
            "col": int(start_col) + 1,
            "end_line": int(end_row) + 1,
            "end_col": int(end_col) + 1,
            "severity": "error",
            "message": "Parse error: unable to parse this section (possibly incomplete or malformed)",
            "tool": "tree-sitter"
        })

    # Also look for MISSING nodes (expected tokens that aren't present)
    missing_pattern = r'MISSING\s+(.+?)\s+\[(\d+),\s*(\d+)\]'

    for match in re.finditer(missing_pattern, output):
        node_type, row, col = match.groups()

        errors.append({
            "file": file_path,
            "line": int(row) + 1,
            "col": int(col) + 1,
            "severity": "warning",
            "message": f"Missing expected token: {node_type}",
            "tool": "tree-sitter"
        })

    return errors


def validate_with_python_library(file_path: str) -> List[Dict[str, Any]]:
    """
    Fallback validation using tree-sitter Python library.

    This is more reliable than CLI parsing but requires the library to be installed.

    Args:
        file_path: Path to source file

    Returns:
        List of error dictionaries
    """
    errors = []

    try:
        from tree_sitter import Language, Parser

        # Detect grammar
        grammar = detect_grammar(file_path)
        if not grammar:
            return [{"error": f"Unsupported file type for tree-sitter: {file_path}"}]

        # Try to load the language
        try:
            # This requires tree-sitter-{language} to be installed
            # e.g., pip install tree-sitter-commonlisp
            if grammar == "commonlisp":
                from tree_sitter_commonlisp import language as commonlisp_language
                lang = commonlisp_language()
            elif grammar == "clojure":
                from tree_sitter_clojure import language as clojure_language
                lang = clojure_language()
            elif grammar == "elisp":
                from tree_sitter_elisp import language as elisp_language
                lang = elisp_language()
            else:
                return [{"error": f"Grammar {grammar} not available in Python"}]

            parser = Parser()
            parser.set_language(lang)

            # Read file
            with open(file_path, 'rb') as f:
                source_code = f.read()

            # Parse
            tree = parser.parse(source_code)

            # Extract errors
            errors.extend(extract_errors_from_tree(tree.root_node, file_path, source_code))

        except ImportError as e:
            return [{"error": f"tree-sitter grammar not installed: {e}"}]

    except ImportError:
        return [{"error": "tree-sitter Python library not found (install: pip install tree-sitter)"}]
    except Exception as e:
        return [{"error": f"tree-sitter Python error: {e}"}]

    return errors


def extract_errors_from_tree(node, file_path: str, source_code: bytes) -> List[Dict[str, Any]]:
    """
    Recursively extract ERROR and MISSING nodes from parse tree.

    Args:
        node: tree-sitter Node object
        file_path: Source file path
        source_code: Source code bytes

    Returns:
        List of error dictionaries
    """
    errors = []

    if node.type == "ERROR":
        # Get the text that failed to parse
        error_text = source_code[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        errors.append({
            "file": file_path,
            "line": node.start_point[0] + 1,
            "col": node.start_point[1] + 1,
            "end_line": node.end_point[0] + 1,
            "end_col": node.end_point[1] + 1,
            "severity": "error",
            "message": f"Parse error in: {error_text[:50]}{'...' if len(error_text) > 50 else ''}",
            "tool": "tree-sitter"
        })

    if node.is_missing:
        errors.append({
            "file": file_path,
            "line": node.start_point[0] + 1,
            "col": node.start_point[1] + 1,
            "severity": "warning",
            "message": f"Missing expected node: {node.type}",
            "tool": "tree-sitter"
        })

    # Recursively check children
    for child in node.children:
        errors.extend(extract_errors_from_tree(child, file_path, source_code))

    return errors


def validate_tree_sitter(file_path: str, use_python: bool = True) -> Dict[str, Any]:
    """
    Validate Lisp code using tree-sitter (handles incomplete code).

    Args:
        file_path: Path to source file
        use_python: Try Python library before falling back to CLI

    Returns:
        Validation results with findings
    """
    result = {
        "target": file_path,
        "dialect": "tree-sitter",
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": ["tree-sitter"]
        }
    }

    # Try Python library first (more reliable)
    if use_python:
        python_errors = validate_with_python_library(file_path)

        if python_errors and "error" in python_errors[0] and len(python_errors[0]) == 2:
            # Fallback to CLI if Python library fails
            if not check_tree_sitter_available():
                if "warnings" not in result:
                    result["warnings"] = []
                result["warnings"].append("tree-sitter not available (neither CLI nor Python library)")
                return result

            cli_result = run_tree_sitter_parse(file_path)

            if "error" in cli_result:
                if "warnings" not in result:
                    result["warnings"] = []
                result["warnings"].append(cli_result["error"])
            else:
                result["findings"] = parse_tree_sitter_output(cli_result["output"], file_path)
        else:
            result["findings"] = python_errors

    else:
        # Use CLI directly
        if not check_tree_sitter_available():
            if "warnings" not in result:
                result["warnings"] = []
            result["warnings"].append("tree-sitter CLI not found")
            return result

        cli_result = run_tree_sitter_parse(file_path)

        if "error" in cli_result:
            if "warnings" not in result:
                result["warnings"] = []
            result["warnings"].append(cli_result["error"])
        else:
            result["findings"] = parse_tree_sitter_output(cli_result["output"], file_path)

    # Count errors and warnings
    for finding in result["findings"]:
        if finding.get("severity") == "error":
            result["summary"]["total_errors"] += 1
        elif finding.get("severity") == "warning":
            result["summary"]["total_warnings"] += 1

    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_tree_sitter.py <file> [--no-python]", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    use_python = "--no-python" not in sys.argv

    result = validate_tree_sitter(file_path, use_python=use_python)

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
