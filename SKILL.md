---
name: lisp-validator
description: Validate Lisp code (Clojure, Racket, Scheme, Common Lisp) for syntax errors, parenthesis balance, and semantic issues. This skill should be used when validating Lisp code files, checking for syntax errors before execution, or validating LLM-generated Lisp code including incomplete or partial expressions. Provides structured JSON output optimized for automated workflows.
license: AGPL 3.0 - Complete terms in LICENSE
---

# Lisp Validator

## Overview

This skill validates Lisp code across multiple dialects (Clojure, Racket, Scheme, Common Lisp) using dialect-specific tools optimized for LLM workflows. Critical for validating incomplete or partially-generated code during LLM-guided editing, it provides structured error output with precise file:line:col information for targeted fixes.

**Key capabilities:**
- Auto-detects Lisp dialect from file extension and content
- Handles incomplete code via tree-sitter (critical for LLM workflows)
- Provides structured JSON output for machine parsing
- Multi-tool validation for comprehensive error detection
- Installation detection and guidance for missing tools

## When to Use This Skill

Use this skill to:
- Validate Lisp code files before execution or commit
- Check LLM-generated Lisp code for syntax errors
- Validate incomplete or partial expressions during code generation
- Detect unbalanced parentheses and structural issues
- Lint entire projects for style and semantic issues
- Determine which validation tools are available on the system

## Workflow Decision Tree

```
┌─ Code complete? ────┐
│                     │
YES                  NO (incomplete/partial)
│                     │
├─ Detect dialect     └─ Use tree-sitter
│                        (handles incomplete)
├─ Clojure? ──→ clj-kondo + joker
├─ Racket/Scheme? ──→ raco tools
├─ Common Lisp? ──→ SBLint + SBCL
├─ Elisp? ──→ tree-sitter
└─ Unknown? ──→ tree-sitter fallback
```

## Quick Start

### Check Available Tools

Before validating, check which tools are installed:

```bash
python3 scripts/check_tools.py
```

This shows:
- Which validation tools are available
- Tool installation status per dialect
- Installation commands for missing tools
- Recommendations based on detected tools

### Validate Any Lisp File (Auto-Detect)

```bash
# Auto-detects dialect and uses appropriate validator
python3 scripts/validate.py <file-or-directory>

# Examples
python3 scripts/validate.py src/core.clj
python3 scripts/validate.py project/src/
```

**Output:** JSON with findings, severity, file:line:col locations

### Format Options

```bash
# JSON output (default, best for parsing)
python3 scripts/validate.py file.clj --format json

# Human-readable text
python3 scripts/validate.py file.clj --format text

# Summary only
python3 scripts/validate.py file.clj --format summary
```

## Dialect-Specific Validation

### Clojure

**Primary tool:** clj-kondo (JSON output, comprehensive)
**Secondary tool:** joker (complementary checks)

```bash
# Using dialect-specific validator
python3 scripts/validate_clojure.py <file-or-directory>

# Skip joker (faster, clj-kondo only)
python3 scripts/validate_clojure.py src/ --no-joker
```

**What it detects:**
- Unbalanced parentheses
- Mismatched delimiters (`{` closed with `)`)
- Unexpected EOF
- Undefined symbols
- Arity mismatches
- Unused bindings
- Style issues

**Output structure:**
```json
{
  "target": "src/core.clj",
  "dialect": "clojure",
  "findings": [
    {
      "file": "src/core.clj",
      "line": 10,
      "col": 15,
      "end_line": 10,
      "end_col": 20,
      "severity": "error",
      "message": "Unexpected EOF.",
      "type": "unexpected-eof",
      "tool": "clj-kondo"
    }
  ],
  "summary": {
    "total_errors": 1,
    "total_warnings": 0,
    "tools_used": ["clj-kondo", "joker"]
  }
}
```

**Exit codes:**
- 0: No issues
- 2: Warnings only
- 3: Errors present

### Racket/Scheme

**Tools used:** raco expand, raco review, raco warn (tiered validation)
**Note:** raco tools work for both Racket and generic Scheme when Racket is installed

```bash
# Using dialect-specific validator
python3 scripts/validate_scheme.py <file-or-directory>

# Force raco tools (default if available)
python3 scripts/validate_scheme.py file.rkt --raco

# Fallback to specific Scheme dialect
python3 scripts/validate_scheme.py file.scm --no-raco --dialect guile
```

**Supported Scheme dialects (when raco unavailable):**
- guile
- chez
- chicken
- mit

**Validation stages:**
1. **Fast check** (raco expand): Safe syntax validation without execution
2. **Surface lint** (raco review): Quick error detection
3. **Deep analysis** (raco warn): Comprehensive warnings with suggestions

**What it detects:**
- Unbound identifiers
- Duplicate bindings
- Arity mismatches
- Type errors (Typed Racket)
- Unused variables
- Style violations

### Common Lisp

**Primary tool:** SBLint (machine-readable output)
**Secondary tool:** SBCL (deep semantic validation)

```bash
# Using dialect-specific validator
python3 scripts/validate_common_lisp.py <file-or-directory>

# Skip SBCL (faster, SBLint only)
python3 scripts/validate_common_lisp.py src/ --no-sbcl
```

**What it detects:**
- Undefined variables
- Undefined functions
- Unused variables
- Style warnings
- Compilation errors
- Read errors (syntax)

**Note:** SBCL provides verbose output requiring parsing; SBLint provides machine-readable format.

### Tree-Sitter (Incomplete Code)

**Critical for LLM workflows:** Handles partial/incomplete expressions

```bash
# Using tree-sitter validator
python3 scripts/validate_tree_sitter.py <file>

# Use Python library (more reliable)
python3 scripts/validate_tree_sitter.py file.lisp

# Use CLI only
python3 scripts/validate_tree_sitter.py file.lisp --no-python
```

**When to use:**
- Code is incomplete (missing closing parens)
- Validating partial expressions during generation
- Traditional validators fail on incomplete code
- Structural validation without semantic analysis

**Supported grammars:**
- Clojure (`tree-sitter-clojure`)
- Common Lisp (`tree-sitter-commonlisp`)
- Emacs Lisp (`tree-sitter-elisp`)

**Output:** Marks ERROR and MISSING nodes in parse tree

## Validation Workflows

### Progressive Validation (Recommended)

Validate in stages from fast to comprehensive:

```bash
# Stage 1: Fast check (< 1s)
python3 scripts/validate_tree_sitter.py file.clj

# Stage 2: Comprehensive (if stage 1 passes)
python3 scripts/validate_clojure.py file.clj

# Stage 3: Auto-format (only if validation passes)
# [Apply formatter like cljfmt, raco fmt, etc.]
```

### Incomplete Code Validation

When validating LLM-generated partial code:

```bash
# Force tree-sitter for incomplete code
python3 scripts/validate.py partial_code.clj --tree-sitter
```

**Interpreting results for incomplete code:**
- ERROR nodes: Unparseable sections
- MISSING nodes: Expected tokens absent
- "Unexpected EOF" is expected for incomplete code

Serious structural errors beyond incompleteness warrant attention.

### Project-Wide Validation

```bash
# Validate entire project (auto-detects files)
python3 scripts/validate.py project/src/

# Clojure project
python3 scripts/validate_clojure.py src/

# Racket package
python3 scripts/validate_scheme.py src/ --raco

# Common Lisp system
python3 scripts/validate_common_lisp.py src/
```

## Using Validation Scripts

### Main Orchestrator

`scripts/validate.py` auto-detects dialect and routes to appropriate validator.

**Options:**
```bash
--dialect <dialect>    Force specific dialect
--tree-sitter          Force tree-sitter (incomplete code)
--format <format>      Output format (json|text|summary)
```

**Examples:**
```bash
# Auto-detect
python3 scripts/validate.py src/

# Force dialect
python3 scripts/validate.py file.scm --dialect scheme

# Incomplete code
python3 scripts/validate.py partial.clj --tree-sitter

# Human-readable output
python3 scripts/validate.py src/ --format text
```

### Dialect-Specific Validators

Each validator provides focused validation for its dialect:

**Clojure:**
```bash
python3 scripts/validate_clojure.py <target> [--no-joker]
```

**Racket/Scheme:**
```bash
python3 scripts/validate_scheme.py <target> [--no-raco] [--dialect <dialect>]
```

**Common Lisp:**
```bash
python3 scripts/validate_common_lisp.py <target> [--no-sbcl]
```

**Tree-sitter:**
```bash
python3 scripts/validate_tree_sitter.py <file> [--no-python]
```

### Tool Checker

`scripts/check_tools.py` shows installation status and provides installation guidance.

```bash
# Text output (default)
python3 scripts/check_tools.py

# JSON output
python3 scripts/check_tools.py --json
```

## Reference Documentation

Detailed information is available in the `references/` directory:

### references/tool_comparison.md

Load this when determining which validation tools to use.

Contains:
- Complete tool comparison matrix
- Detailed tool profiles (installation, usage, output formats)
- Dialect-specific recommendations
- Performance comparison
- Exit code standards
- Optimal tool combinations for LLM workflows

**Use when:**
- Selecting validation tools for a project
- Understanding tool capabilities and limitations
- Comparing different validators
- Setting up CI/CD pipelines

### references/error_patterns.md

Load this when parsing validation tool output.

Contains:
- Regex patterns for each tool's output format
- Structured output formats (JSON, parseable text)
- Unstructured output parsing strategies (SBCL, Scheme dialects)
- Unified error schema for normalization
- Common error types by dialect
- Edge cases and parsing best practices

**Use when:**
- Parsing validation output programmatically
- Normalizing errors across multiple tools
- Implementing custom error handlers
- Debugging parsing issues

### references/integration_strategies.md

Load this when integrating validation into LLM workflows.

Contains:
- Core principles (progressive validation, structured output)
- Dialect-specific strategies and pipelines
- LLM-specific patterns (edit validation loop, partial expression validation)
- CI/CD integration examples
- Performance optimization techniques
- Error recovery strategies

**Use when:**
- Implementing LLM-guided code editing workflows
- Setting up automated validation pipelines
- Optimizing validation performance
- Handling validation errors in LLM context

## Interpreting Validation Results

### Error Severity Levels

- **error**: Code will not run (syntax errors, undefined symbols)
- **warning**: Code may run but has issues (unused variables, style)
- **info**: Informational messages (suggestions, style recommendations)

### Common Error Types

**Unbalanced parentheses:**
```
error: Unexpected EOF (missing closing parenthesis)
error: Unmatched delimiter: )
```

**Undefined symbols:**
```
error: Unresolved symbol: foo
error: Unbound variable: bar
```

**Arity mismatches:**
```
error: Wrong number of args (3) passed to function (expects 2)
```

### Acting on Validation Results

1. **Errors first:** Fix syntax and structural errors before warnings
2. **Location precision:** Use file:line:col to locate exact problem
3. **Suggestions:** Some tools (raco warn) provide fix suggestions
4. **Multiple tools:** Different tools may catch different issues
5. **Incomplete code:** Distinguish between "incomplete" and "invalid"

## Installation Guidance

### Recommended Tools by Dialect

**Clojure:**
```bash
# Primary: clj-kondo
brew install borkdude/brew/clj-kondo
# Or: npm install -g clj-kondo

# Secondary: joker
brew install candid82/joker/joker
```

**Racket/Scheme:**
```bash
# Install Racket (provides raco)
brew install racket  # macOS
# Or download from: https://racket-lang.org

# Install raco packages
raco pkg install review syntax-warn
```

**Common Lisp:**
```bash
# Install Roswell
brew install roswell  # macOS

# Install SBCL and SBLint
ros install sbcl
ros use sbcl
ros install cxxxr/sblint
```

**Universal (all dialects):**
```bash
# tree-sitter CLI
npm install -g tree-sitter-cli@0.19.3

# tree-sitter Python library (more reliable)
pip install tree-sitter tree-sitter-commonlisp tree-sitter-clojure tree-sitter-elisp
```

### Checking Installation Status

Always check which tools are available before validating:

```bash
python3 scripts/check_tools.py
```

This provides:
- Installation status per tool
- Platform-specific installation commands
- Dialect-specific recommendations
- Warnings for missing high-priority tools

## Best Practices

1. **Check tools first:** Run `check_tools.py` to verify available validators
2. **Use structured output:** JSON format for programmatic parsing
3. **Validate incrementally:** After each code edit in LLM workflows
4. **Handle incomplete code:** Use tree-sitter for partial expressions
5. **Combine tools:** Multiple validators catch different error types
6. **Read references:** Load relevant reference docs for detailed guidance
7. **Interpret exit codes:** 0=success, 2=warnings, 3=errors
8. **Fix errors before warnings:** Prioritize structural issues
9. **Use progressive validation:** Fast check → comprehensive → auto-fix
10. **Cache when possible:** clj-kondo and raco warn support caching

## Exit Codes

All validation scripts use consistent exit codes:

- **0**: Validation passed (no errors or warnings)
- **2**: Warnings only (code should run)
- **3**: Errors present (code may not run)

Use these for automation:

```bash
if python3 scripts/validate.py src/; then
    echo "✓ Validation passed"
else
    exit_code=$?
    if [ $exit_code -eq 2 ]; then
        echo "⚠ Warnings present"
    elif [ $exit_code -eq 3 ]; then
        echo "✗ Errors found"
    fi
fi
```

## Troubleshooting

**"Tool not found" errors:**
- Run `check_tools.py` to see installation status
- Follow installation commands for your platform
- Verify tool is in PATH

**"Cannot parse output" errors:**
- Check tool version (some have breaking changes)
- tree-sitter CLI: use version 0.19.3 (not 0.20+)
- Try alternate tool for same dialect

**"Unexpected EOF" on complete code:**
- Code may have hidden syntax errors
- Use tree-sitter to identify exact location
- Check for unmatched delimiters earlier in file

**False positives:**
- Some tools (joker) may flag macro-introduced bindings
- Cross-reference with multiple tools
- Use dialect-specific validators over generic ones

**Performance issues:**
- Use `--no-joker` or `--no-sbcl` flags to skip secondary tools
- Validate changed files only (use clj-kondo caching)
- Run validations in parallel for large projects
