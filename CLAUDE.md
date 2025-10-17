# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Skill** that provides comprehensive Lisp code validation across multiple dialects (Clojure, Racket, Scheme, Common Lisp, Emacs Lisp). The skill is optimized for LLM workflows and can handle incomplete/partial code via tree-sitter parsing.

**Key differentiator:** Unlike traditional validators, this skill validates incomplete code expressions during generation, making it ideal for LLM-guided code editing workflows.

**License:** AGPL 3.0 - All Python scripts include copyright headers. See LICENSE file for complete terms.

## Using This Skill

This skill can be used in:
- **Claude.ai**: Upload via Skills settings (see Installation below)
- **Claude Code**: Install via `./install.sh` or manually copy to ~/.claude/skills/
- **Claude API**: Upload as custom skill via Skills API

See `SKILL.md` for complete skill documentation including:
- When to use this skill
- Workflow decision trees
- Validation strategies
- Reference documentation guides

## Installation & Packaging

### Package the Skill

```bash
./package.sh
```

Creates `lisp-validator.zip` (60KB) containing:
- SKILL.md, LICENSE, README.md, CLAUDE.md
- scripts/ directory with all validators
- references/ directory with documentation
- Excludes development files (.git, __pycache__, etc.)

### Install to Claude Code

```bash
./install.sh
```

Installs skill to `~/.claude/skills/lisp-validator/` with:
- Automatic directory creation
- Overwrite protection (prompts before replacing)
- Executable permissions set on scripts
- Installation verification

### Uninstall from Claude Code

```bash
./uninstall.sh
```

Removes skill from `~/.claude/skills/lisp-validator/` with confirmation prompt.

## Common Commands

### Check Available Tools
```bash
python3 scripts/check_tools.py
```
Shows which validation tools are installed and provides installation guidance.

### Validate Code (Auto-Detect Dialect)
```bash
# Auto-detect dialect from file extension/content
python3 scripts/validate.py <file-or-directory>

# Force specific dialect
python3 scripts/validate.py <file-or-directory> --dialect clojure

# Validate incomplete code (uses tree-sitter)
python3 scripts/validate.py <file> --tree-sitter

# Human-readable output
python3 scripts/validate.py <file-or-directory> --format text
```

### Dialect-Specific Validation
```bash
# Clojure (clj-kondo + joker)
python3 scripts/validate_clojure.py <target> [--no-joker]

# Racket/Scheme (raco tools)
python3 scripts/validate_scheme.py <target> [--no-raco] [--dialect <dialect>]

# Common Lisp (SBLint + SBCL)
python3 scripts/validate_common_lisp.py <target> [--no-sbcl]

# Tree-sitter (incomplete code)
python3 scripts/validate_tree_sitter.py <file> [--no-python]
```

## Architecture

### Script Organization

The codebase follows a modular architecture with clear separation of concerns:

1. **Main Orchestrator** (`scripts/validate.py`)
   - Auto-detects Lisp dialect via extension and content analysis
   - Routes to dialect-specific validators
   - Provides unified output format across all validators
   - Handles force-dialect and tree-sitter fallback modes

2. **Dialect-Specific Validators** (`scripts/validate_*.py`)
   - Each dialect has a dedicated validator module
   - Multi-tool validation strategy (primary + secondary tools)
   - Normalizes tool-specific output to unified JSON schema
   - Deduplicates findings across tools using file:line:col matching
   - Sort findings by (file, line, col) for consistent output

3. **Tool Detection** (`scripts/check_tools.py`)
   - Detects available validation tools on the system
   - Provides platform-specific installation commands
   - Generates dialect-specific recommendations
   - Supports both JSON and human-readable output

### Validation Flow

```
User Input (file/directory)
    ↓
validate.py (orchestrator)
    ↓
Dialect Detection (extension → content analysis)
    ↓
Route to Validator:
    ├─ Clojure → clj-kondo (primary) + joker (secondary)
    ├─ Scheme/Racket → raco expand/review/warn
    ├─ Common Lisp → SBLint (primary) + SBCL (secondary)
    ├─ Incomplete Code → tree-sitter (Python lib or CLI)
    └─ Unknown → tree-sitter fallback
    ↓
Normalize Findings (unified schema)
    ↓
Output JSON (file:line:col precision)
```

### Unified Error Schema

All validators normalize their output to this schema:

```python
{
  "target": str,           # Input file/directory
  "dialect": str,          # Detected/forced dialect
  "findings": [            # List of issues
    {
      "file": str,         # File path
      "line": int,         # Line number (1-indexed)
      "col": int,          # Column number (1-indexed)
      "end_line": int?,    # Optional end location
      "end_col": int?,     # Optional end location
      "severity": str,     # "error" | "warning" | "info"
      "message": str,      # Human-readable message
      "type": str,         # Error type identifier
      "tool": str          # Source tool name
    }
  ],
  "summary": {
    "total_errors": int,   # Count of errors
    "total_warnings": int, # Count of warnings
    "tools_used": [str]    # List of tools executed
  },
  "warnings": [str]?       # Optional system warnings
}
```

### Dialect Detection Logic

The auto-detection system uses a two-phase approach:

1. **Extension-based detection** (fast, reliable)
   - `.clj`, `.cljs`, `.cljc` → Clojure
   - `.rkt` → Racket
   - `.scm`, `.ss` → Scheme
   - `.lisp`, `.cl`, `.asd` → Common Lisp
   - `.el` → Emacs Lisp

2. **Content-based detection** (fallback, heuristic)
   - Clojure: `(ns ...)`, `[... :as ...]`, `::`
   - Racket: `#lang racket`, `(module ...)`
   - Common Lisp: `(defpackage ...)`, `(in-package ...)`, `(defsystem ...)`
   - Scheme: `(define-module ...)`

If both fail, falls back to tree-sitter for generic parsing.

## Tool Integration Strategy

### Multi-Tool Validation

Each dialect uses multiple complementary tools:

- **Clojure**: clj-kondo (comprehensive, JSON output) + joker (complementary checks)
- **Racket/Scheme**: raco expand (fast) → raco review (surface) → raco warn (deep)
- **Common Lisp**: SBLint (machine-readable) + SBCL (semantic)
- **Universal**: tree-sitter (handles incomplete code)

### Deduplication Strategy

When running multiple tools, findings are deduplicated by comparing (file, line, col) tuples. This prevents reporting the same issue multiple times from different tools.

### Tool Fallback Behavior

Each validator handles missing tools gracefully:
- Adds warnings to output when tools are unavailable
- Continues with available tools
- Provides installation guidance via `check_tools.py`
- Returns partial results rather than failing completely

## Exit Codes

All scripts use consistent exit codes:
- **0**: Validation passed (no errors or warnings)
- **2**: Warnings only (code should run but has style/minor issues)
- **3**: Errors present (code may not run correctly)

## Important Context for Development

### Repository Structure

```
lisp-validator/
├── SKILL.md                      # Main skill file (YAML frontmatter + instructions)
├── LICENSE                       # Full AGPL 3.0 license text
├── README.md                     # GitHub documentation
├── CLAUDE.md                     # This file (Claude Code guidance)
├── package.sh                    # Create distributable zip (60KB)
├── install.sh                    # Install to Claude Code
├── uninstall.sh                  # Remove from Claude Code
├── scripts/                      # All validation scripts (with copyright headers)
│   ├── validate.py              # Main orchestrator (auto-detect)
│   ├── check_tools.py           # Tool detection and installation guidance
│   ├── validate_clojure.py      # Clojure validator (clj-kondo + joker)
│   ├── validate_common_lisp.py  # Common Lisp validator (SBLint + SBCL)
│   ├── validate_scheme.py       # Racket/Scheme validator (raco tools)
│   └── validate_tree_sitter.py  # Tree-sitter validator (incomplete code)
└── references/                   # Reference documentation
    ├── tool_comparison.md       # Tool selection guide
    ├── error_patterns.md        # Parsing strategies
    └── integration_strategies.md # LLM workflow patterns
```

### Reference Documentation

The `references/` directory contains critical implementation details. Each file has a header explaining when to load it:

- **`tool_comparison.md`**: Complete tool matrix, capabilities, output formats, performance comparison. **Load when:** selecting or modifying tool integrations, setting up CI/CD, troubleshooting tool-specific issues.

- **`error_patterns.md`**: Regex patterns for parsing tool output, edge cases, structured vs unstructured format handling. **Load when:** adding new tools, debugging parsing issues, normalizing errors across multiple tools.

- **`integration_strategies.md`**: LLM workflow patterns, progressive validation pipelines, CI/CD integration examples. **Load when:** implementing new validation workflows, optimizing performance, handling validation errors in LLM context.

### Progressive Validation Pattern

The tool supports a fast-to-comprehensive validation workflow:

1. **Fast check** (< 1s): tree-sitter for structural validation
2. **Comprehensive** (1-5s): dialect-specific validators
3. **Auto-format** (optional): Run formatters only after validation passes

This pattern is critical for LLM workflows where rapid iteration is required.

### Incomplete Code Handling

Tree-sitter is the **only** tool that can validate incomplete code:
- Traditional validators (clj-kondo, raco, SBLint) require syntactically complete code
- Tree-sitter marks ERROR and MISSING nodes in the parse tree
- Use `--tree-sitter` flag to force tree-sitter validation
- "Unexpected EOF" on incomplete code is expected behavior

When adding new features that validate during code generation, always consider the incomplete code path.

## Testing Considerations

When modifying validators:

1. **Test with multiple tools**: Each dialect uses 2+ tools; test both primary and secondary
2. **Test incomplete code**: Use tree-sitter path with partial expressions
3. **Test deduplication**: Verify findings from multiple tools are properly merged
4. **Test exit codes**: Ensure proper codes (0/2/3) based on findings
5. **Test dialect detection**: Verify both extension and content-based detection
6. **Test tool absence**: Ensure graceful degradation when tools are missing

## Python Implementation Notes

- All scripts use Python 3.x with minimal dependencies (only tree-sitter Python lib is optional)
- Module imports use dynamic loading to handle both package and script execution modes
- Subprocess timeouts prevent hanging on malformed input
- JSON output is preferred for machine parsing; text format is for human readability
- Error handling follows the pattern: try tool → capture error → add to warnings → continue
- All scripts include AGPL 3.0 copyright headers (Copyright (C) 2025 Tom Waddington)

## Contributing and Modifications

When modifying this skill:

1. **Maintain license compliance**: All new code must be AGPL 3.0 compatible and include copyright headers
2. **Update SKILL.md**: Ensure the main skill documentation reflects any changes
3. **Test comprehensively**: Follow testing considerations above
4. **Update references**: If adding tools or changing behavior, update relevant reference docs
5. **Preserve incomplete code handling**: This is a core feature - don't break it
6. **Keep unified schema**: All validators must normalize to the unified error schema

## License

This skill is licensed under AGPL 3.0. Key requirements:
- **Source availability**: Modified versions must provide source code
- **Network use**: If you run a modified version on a server, users must be able to get the source
- **Copyleft**: Derivative works must also be AGPL 3.0
- **Attribution**: Copyright notices must be preserved

See LICENSE file for complete terms.
