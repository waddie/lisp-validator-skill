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
Shared type definitions and constants for validation scripts.
"""

from typing import TypedDict, Optional, List, Literal, Dict, Any

# Type definitions
SeverityLevel = Literal["error", "warning", "info"]


class Finding(TypedDict, total=False):
    """
    A single validation finding (error, warning, or info).

    Required fields:
        file: Path to the file containing the finding
        line: Line number (1-indexed)
        col: Column number (1-indexed)
        severity: Severity level
        message: Human-readable error message
        tool: Name of the tool that generated this finding

    Optional fields:
        end_line: End line number for multi-line findings
        end_col: End column number for multi-line findings
        type: Error type identifier (e.g., "unexpected-eof")
    """
    file: str
    line: int
    col: int
    end_line: int
    end_col: int
    severity: SeverityLevel
    message: str
    type: str
    tool: str


class ValidationSummary(TypedDict):
    """
    Summary statistics for validation results.

    Fields:
        total_errors: Count of error-level findings
        total_warnings: Count of warning-level findings
        tools_used: List of tool names that were executed
    """
    total_errors: int
    total_warnings: int
    tools_used: List[str]


class ValidationResult(TypedDict, total=False):
    """
    Complete validation result structure.

    Required fields:
        target: Input file or directory path
        dialect: Detected or forced dialect name
        findings: List of validation findings
        summary: Summary statistics

    Optional fields:
        detected_dialect: Auto-detected dialect (when different from forced)
        warnings: System warnings (e.g., "tool not found")
        error: Fatal error message (when validation cannot proceed)
    """
    target: str
    dialect: str
    detected_dialect: str
    findings: List[Finding]
    summary: ValidationSummary
    warnings: List[str]
    error: str


# Constants
DIALECT_DETECTION_BYTES = 1024  # Read first 1KB for dialect detection
CLJ_KONDO_TIMEOUT_SECONDS = 30
JOKER_TIMEOUT_SECONDS = 10
TREE_SITTER_TIMEOUT_SECONDS = 30
RACO_TIMEOUT_SECONDS = 30
SBLINT_TIMEOUT_SECONDS = 30
SBCL_TIMEOUT_SECONDS = 60
TOOL_CHECK_TIMEOUT_SECONDS = 5
MAX_ERROR_TEXT_LENGTH = 50  # Maximum length of error text in messages
MAX_SBCL_MESSAGE_LENGTH = 500  # Maximum length of SBCL error messages

# Exit codes
EXIT_SUCCESS = 0  # No issues found
EXIT_WARNINGS = 2  # Warnings only (code should run)
EXIT_ERRORS = 3  # Errors present (code may not run)

# File extensions
CLOJURE_EXTENSIONS = {".clj", ".cljs", ".cljc", ".edn"}
RACKET_EXTENSIONS = {".rkt"}
SCHEME_EXTENSIONS = {".scm", ".ss"}
COMMON_LISP_EXTENSIONS = {".lisp", ".cl", ".asd"}
ELISP_EXTENSIONS = {".el"}

# Dialect names
DIALECT_CLOJURE = "clojure"
DIALECT_RACKET = "racket"
DIALECT_SCHEME = "scheme"
DIALECT_COMMON_LISP = "common-lisp"
DIALECT_ELISP = "elisp"
DIALECT_UNKNOWN = "unknown"


# Helper functions
def create_tool_not_found_error(tool_name: str, install_cmd: Optional[str] = None) -> Dict[str, str]:
    """
    Create a standardized tool-not-found error message.

    Args:
        tool_name: Name of the missing tool
        install_cmd: Optional installation command

    Returns:
        Error dictionary with standardized format
    """
    msg = f"{tool_name} not found"
    if install_cmd:
        msg += f" (install: {install_cmd})"
    return {"error": msg, "tool": tool_name}


def create_empty_result(target: str, dialect: str) -> ValidationResult:
    """
    Create an empty validation result structure.

    Args:
        target: Target file or directory
        dialect: Dialect name

    Returns:
        Empty ValidationResult dictionary
    """
    return {
        "target": target,
        "dialect": dialect,
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": []
        }
    }


def create_error_result(target: str, error_message: str, dialect: str = DIALECT_UNKNOWN) -> ValidationResult:
    """
    Create a validation result with a fatal error.

    Args:
        target: Target file or directory
        error_message: Error message
        dialect: Dialect name (default: unknown)

    Returns:
        ValidationResult with error
    """
    return {
        "error": error_message,
        "target": target,
        "dialect": dialect,
        "findings": [],
        "summary": {
            "total_errors": 0,
            "total_warnings": 0,
            "tools_used": []
        }
    }
