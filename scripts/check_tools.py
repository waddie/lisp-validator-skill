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
Detect installed Lisp validation tools and provide installation guidance.
"""

import subprocess
import sys
import json
import platform
from typing import Dict, List, Tuple, Optional


def check_command(command: str, args: List[str] = ["--version"]) -> Tuple[bool, Optional[str]]:
    """
    Check if a command is available.

    Args:
        command: Command name to check
        args: Arguments to test command

    Returns:
        Tuple of (available, version_info)
    """
    try:
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            text=True,
            timeout=5
        )
        return True, result.stdout.strip()
    except FileNotFoundError:
        return False, None
    except subprocess.TimeoutExpired:
        return True, "available (version check timed out)"
    except Exception:
        return False, None


def get_platform_install_cmd(tool: str) -> Dict[str, str]:
    """
    Get platform-specific installation commands.

    Args:
        tool: Tool name

    Returns:
        Dict of platform -> install command
    """
    install_commands = {
        "clj-kondo": {
            "darwin": "brew install borkdude/brew/clj-kondo",
            "linux": "curl -sLO https://raw.githubusercontent.com/borkdude/clj-kondo/master/script/install-clj-kondo && chmod +x install-clj-kondo && ./install-clj-kondo",
            "windows": "npm install -g clj-kondo",
            "universal": "npm install -g clj-kondo"
        },
        "joker": {
            "darwin": "brew install candid82/joker/joker",
            "linux": "Download from: https://github.com/candid82/joker/releases",
            "windows": "Download from: https://github.com/candid82/joker/releases",
            "universal": "Download binary from: https://github.com/candid82/joker/releases"
        },
        "raco": {
            "darwin": "brew install racket",
            "linux": "apt install racket (Ubuntu/Debian) or download from: https://racket-lang.org",
            "windows": "Download installer from: https://racket-lang.org",
            "universal": "Install Racket from: https://racket-lang.org"
        },
        "sblint": {
            "universal": "ros install sbcl && ros use sbcl && ros install cxxxr/sblint"
        },
        "sbcl": {
            "darwin": "brew install sbcl or ros install sbcl",
            "linux": "apt install sbcl (Ubuntu/Debian) or ros install sbcl",
            "windows": "Download from: http://www.sbcl.org or use Roswell",
            "universal": "ros install sbcl or download from: http://www.sbcl.org"
        },
        "tree-sitter": {
            "universal": "npm install -g tree-sitter-cli@0.19.3"
        },
        "tree-sitter-python": {
            "universal": "pip install tree-sitter tree-sitter-commonlisp tree-sitter-clojure tree-sitter-elisp"
        }
    }

    return install_commands.get(tool, {})


def check_tools() -> Dict[str, Dict]:
    """
    Check all Lisp validation tools.

    Returns:
        Dict of tool statuses and recommendations
    """
    tools = {
        "clj-kondo": {
            "check_cmd": ["clj-kondo", "--version"],
            "description": "Primary Clojure validator with JSON output",
            "dialects": ["clojure"],
            "priority": "high"
        },
        "joker": {
            "check_cmd": ["joker", "--version"],
            "description": "Secondary Clojure validator with complementary checks",
            "dialects": ["clojure"],
            "priority": "medium"
        },
        "raco": {
            "check_cmd": ["raco", "version"],
            "description": "Racket/Scheme validation tools (expand, review, warn)",
            "dialects": ["racket", "scheme"],
            "priority": "high"
        },
        "sblint": {
            "check_cmd": ["sblint", "--version"],
            "description": "Primary Common Lisp linter with machine-readable output",
            "dialects": ["common-lisp"],
            "priority": "high"
        },
        "sbcl": {
            "check_cmd": ["sbcl", "--version"],
            "description": "Common Lisp compiler for deep semantic validation",
            "dialects": ["common-lisp"],
            "priority": "medium"
        },
        "tree-sitter": {
            "check_cmd": ["tree-sitter", "--version"],
            "description": "Universal parser for incomplete/partial code (CLI)",
            "dialects": ["all"],
            "priority": "high"
        }
    }

    result = {}

    for tool, info in tools.items():
        available, version = check_command(info["check_cmd"][0], info["check_cmd"][1:])

        result[tool] = {
            "available": available,
            "version": version,
            "description": info["description"],
            "dialects": info["dialects"],
            "priority": info["priority"],
            "install": get_platform_install_cmd(tool)
        }

    # Check Python tree-sitter library separately
    try:
        import tree_sitter
        result["tree-sitter-python"] = {
            "available": True,
            "version": tree_sitter.__version__ if hasattr(tree_sitter, '__version__') else "installed",
            "description": "Tree-sitter Python library (more reliable than CLI)",
            "dialects": ["all"],
            "priority": "high",
            "install": get_platform_install_cmd("tree-sitter-python")
        }
    except ImportError:
        result["tree-sitter-python"] = {
            "available": False,
            "version": None,
            "description": "Tree-sitter Python library (more reliable than CLI)",
            "dialects": ["all"],
            "priority": "high",
            "install": get_platform_install_cmd("tree-sitter-python")
        }

    return result


def generate_recommendations(tools: Dict[str, Dict]) -> Dict[str, List[str]]:
    """
    Generate dialect-specific tool recommendations.

    Args:
        tools: Tool status dict

    Returns:
        Dict of dialect -> list of recommendations
    """
    recommendations = {
        "clojure": [],
        "racket": [],
        "scheme": [],
        "common-lisp": [],
        "elisp": [],
        "universal": []
    }

    # Clojure
    if not tools["clj-kondo"]["available"]:
        recommendations["clojure"].append("⚠️  Install clj-kondo (primary Clojure validator)")
    if not tools["joker"]["available"]:
        recommendations["clojure"].append("ℹ️  Consider installing joker (complementary checks)")

    # Racket/Scheme
    if not tools["raco"]["available"]:
        recommendations["racket"].append("⚠️  Install Racket (provides raco tools)")
        recommendations["scheme"].append("ℹ️  Install Racket for raco tools (works with generic Scheme)")

    # Common Lisp
    if not tools["sblint"]["available"]:
        recommendations["common-lisp"].append("⚠️  Install sblint (primary Common Lisp linter)")
    if not tools["sbcl"]["available"]:
        recommendations["common-lisp"].append("ℹ️  Consider installing SBCL (deep validation)")

    # Universal
    if not tools["tree-sitter"]["available"] and not tools.get("tree-sitter-python", {}).get("available"):
        recommendations["universal"].append("⚠️  Install tree-sitter (critical for incomplete code)")
    elif tools["tree-sitter"]["available"] and not tools.get("tree-sitter-python", {}).get("available"):
        recommendations["universal"].append("ℹ️  Consider tree-sitter Python library (more reliable)")

    return recommendations


def format_output(tools: Dict[str, Dict], recommendations: Dict[str, List[str]], output_format: str = "text") -> str:
    """
    Format tool check results.

    Args:
        tools: Tool status dict
        recommendations: Recommendations dict
        output_format: Output format (text|json)

    Returns:
        Formatted string
    """
    if output_format == "json":
        return json.dumps({
            "tools": tools,
            "recommendations": recommendations,
            "platform": platform.system().lower()
        }, indent=2)

    # Text format
    lines = []
    lines.append("=== Lisp Validation Tools Status ===\n")

    # Group by dialect
    for dialect in ["clojure", "racket/scheme", "common-lisp", "universal"]:
        lines.append(f"{dialect.upper()}:")

        for tool, info in tools.items():
            if dialect == "universal" and "all" in info["dialects"]:
                status = "✓" if info["available"] else "✗"
                version = f" ({info['version']})" if info["version"] else ""
                lines.append(f"  [{status}] {tool}{version}")
                lines.append(f"      {info['description']}")

            elif dialect == "racket/scheme" and any(d in info["dialects"] for d in ["racket", "scheme"]):
                status = "✓" if info["available"] else "✗"
                version = f" ({info['version']})" if info["version"] else ""
                lines.append(f"  [{status}] {tool}{version}")
                lines.append(f"      {info['description']}")

            elif dialect in info["dialects"]:
                status = "✓" if info["available"] else "✗"
                version = f" ({info['version']})" if info["version"] else ""
                lines.append(f"  [{status}] {tool}{version}")
                lines.append(f"      {info['description']}")

        lines.append("")

    # Show recommendations
    lines.append("=== Recommendations ===\n")

    for dialect, recs in recommendations.items():
        if recs:
            lines.append(f"{dialect.upper()}:")
            for rec in recs:
                lines.append(f"  {rec}")
            lines.append("")

    # Show installation instructions for missing high-priority tools
    lines.append("=== Installation Instructions ===\n")
    current_platform = platform.system().lower()

    for tool, info in tools.items():
        if not info["available"] and info["priority"] == "high":
            lines.append(f"{tool}:")

            install_cmds = info["install"]
            if current_platform in install_cmds:
                lines.append(f"  {install_cmds[current_platform]}")
            elif "universal" in install_cmds:
                lines.append(f"  {install_cmds['universal']}")

            lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    output_format = "text"

    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        output_format = "json"

    tools = check_tools()
    recommendations = generate_recommendations(tools)

    print(format_output(tools, recommendations, output_format))


if __name__ == "__main__":
    main()
