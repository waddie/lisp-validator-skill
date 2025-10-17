# Integration Strategies for LLM Workflows

**Purpose:** This reference document provides best practices and implementation patterns for integrating Lisp validation tools into LLM-guided code editing workflows, CI/CD pipelines, and automated validation systems.

**When to load this file:**
- Implementing LLM-guided code editing workflows
- Setting up automated validation pipelines
- Optimizing validation performance for large projects
- Designing progressive validation strategies
- Handling validation errors in LLM context
- Integrating validation into CI/CD systems

**What's inside:**
- Core principles (progressive validation, structured output, incomplete code handling)
- Dialect-specific validation strategies and pipelines
- LLM-specific patterns (edit validation loop, partial expression validation, error ranking)
- CI/CD integration examples (GitHub Actions, pre-commit hooks)
- Performance optimization techniques (parallel validation, caching)
- Error recovery strategies and graceful degradation

## Core Principles

### 1. Progressive Validation

Validate code in stages from fast to comprehensive:

```
Fast Check → Comprehensive Check → Auto-Fix
  (< 1s)         (1-5s)              (only if valid)
```

**Benefits:**
- Early failure detection
- Efficient use of resources
- Clear feedback at each stage

**Example Pipeline (Clojure):**
```bash
# Stage 1: Fast syntax check with tree-sitter
validate_tree_sitter.py file.clj

# Stage 2: Comprehensive linting
validate_clojure.py file.clj

# Stage 3: Auto-format (only if stages 1-2 pass)
clj -Tcljfmt fix
```

### 2. Structured Output First

Prioritize tools with machine-readable output for reliable LLM parsing:

**Preference Order:**
1. **JSON/EDN** (clj-kondo) - Most reliable
2. **Structured text** (file:line:col:message) - Good
3. **Verbose text** (SBCL, Scheme) - Requires complex parsing

**Why:** Structured formats eliminate ambiguity and parsing errors in LLM interpretation.

### 3. Incomplete Code Handling

LLM workflows often involve partial or incomplete code during generation. Use tools designed for this:

**Primary:** tree-sitter (handles incomplete expressions)
**Fallback:** Dialect-specific validators (for complete code)

**Decision Logic:**
```python
if is_code_complete(content):
    # Use dialect-specific validator
    result = validate_clojure(file)
else:
    # Use tree-sitter for incomplete code
    result = validate_tree_sitter(file)
```

### 4. Separation of Concerns

**Validate → Analyze → Fix**

Never mix validation and modification in the same step:

```python
# Good: Separate steps
errors = validate(file)
if errors:
    report_errors(errors)
else:
    apply_formatting(file)

# Bad: Mixed concerns
fix_and_validate(file)  # Which errors were pre-existing?
```

## Dialect-Specific Strategies

### Clojure Workflows

#### Optimal Tool Combination

```python
def validate_clojure_for_llm(file_path):
    """LLM-optimized Clojure validation."""

    # Check if code is complete
    with open(file_path) as f:
        content = f.read()

    if has_unmatched_parens(content):
        # Use tree-sitter for incomplete code
        result = validate_tree_sitter(file_path)
    else:
        # Use clj-kondo for complete code
        result = validate_clojure(file_path, use_joker=True)

    # Parse JSON output
    findings = result["findings"]

    # Group by severity
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": f"{len(errors)} errors, {len(warnings)} warnings"
    }
```

#### Incremental Validation

Use clj-kondo's caching for efficient re-validation:

```bash
# First run: analyzes all files, creates .clj-kondo/ cache
clj-kondo --lint src/

# Subsequent runs: only re-analyzes changed files
clj-kondo --lint src/
```

**LLM Benefit:** After each edit, only validate what changed.

#### JSON Parsing Example

```python
import json

def parse_clj_kondo_json(output):
    """Extract structured errors from clj-kondo."""
    data = json.loads(output)

    errors = []
    for finding in data.get("findings", []):
        errors.append({
            "file": finding["filename"],
            "line": finding["row"],
            "col": finding["col"],
            "severity": finding["level"],
            "message": finding["message"],
            "type": finding.get("type"),
            "end_line": finding.get("end-row"),
            "end_col": finding.get("end-col")
        })

    return {
        "errors": errors,
        "summary": data.get("summary", {}),
        "total_errors": data["summary"].get("error", 0),
        "total_warnings": data["summary"].get("warning", 0)
    }
```

### Racket/Scheme Workflows

#### Tiered Validation Pipeline

```bash
#!/bin/bash
# racket_validate_pipeline.sh

FILE=$1

# Stage 1: Fast syntax check (< 1s)
if ! raco expand "$FILE" > /dev/null 2>&1; then
    echo "Syntax error detected"
    raco expand "$FILE" 2>&1
    exit 1
fi

# Stage 2: Surface lint (< 2s)
if ! raco review "$FILE"; then
    echo "Linting issues found"
    exit 2
fi

# Stage 3: Deep analysis (< 5s)
if ! raco warn "$FILE"; then
    echo "Warnings detected"
    exit 3
fi

echo "All checks passed"
exit 0
```

#### Error Aggregation

```python
def validate_racket_comprehensive(file_path):
    """Aggregate results from multiple raco tools."""

    results = {
        "errors": [],
        "warnings": [],
        "tools_used": []
    }

    # Run raco expand
    expand_errors = parse_raco_expand(file_path)
    results["errors"].extend(expand_errors)
    results["tools_used"].append("raco-expand")

    # Only proceed if syntax is valid
    if not expand_errors:
        # Run raco review
        review_errors = parse_raco_review(file_path)
        results["errors"].extend([e for e in review_errors if e["severity"] == "error"])
        results["warnings"].extend([e for e in review_errors if e["severity"] == "warning"])
        results["tools_used"].append("raco-review")

        # Run raco warn
        warn_errors = parse_raco_warn(file_path)
        results["warnings"].extend(warn_errors)
        results["tools_used"].append("raco-warn")

    return results
```

### Common Lisp Workflows

#### SBLint + SBCL Strategy

```python
def validate_common_lisp_thorough(file_path):
    """Combine SBLint and SBCL for comprehensive validation."""

    results = {"errors": [], "warnings": []}

    # Primary: SBLint (fast, machine-readable)
    sblint_errors = run_sblint(file_path)
    results["errors"].extend(parse_sblint_output(sblint_errors))

    # Secondary: SBCL (deep semantic analysis)
    # Only run if SBLint passed or for additional validation
    if not results["errors"] or deep_validation_needed():
        sbcl_errors = run_sbcl_compile(file_path)
        results["errors"].extend(parse_sbcl_output(sbcl_errors))

    # Deduplicate by message
    seen = set()
    unique_errors = []
    for error in results["errors"]:
        key = (error["file"], error["line"], error["message"])
        if key not in seen:
            seen.add(key)
            unique_errors.append(error)

    results["errors"] = unique_errors
    return results
```

## LLM-Specific Patterns

### 1. Edit Validation Loop

After each LLM code edit, validate incrementally:

```python
def llm_edit_validation_loop(file_path, llm_edit_function):
    """Validate after each LLM edit."""

    iteration = 0
    max_iterations = 5

    while iteration < max_iterations:
        # Apply LLM edit
        llm_edit_function(file_path)

        # Validate immediately
        result = validate(file_path)

        if result["valid"]:
            print(f"✓ Edit successful after {iteration + 1} iterations")
            return True

        # Provide errors back to LLM
        error_summary = format_errors_for_llm(result["errors"])
        print(f"✗ Validation failed: {error_summary}")

        # LLM tries to fix based on errors
        iteration += 1

    print(f"✗ Failed to produce valid code after {max_iterations} attempts")
    return False
```

### 2. Partial Expression Validation

When LLM is generating code incrementally:

```python
def validate_partial_code(partial_code_string):
    """Validate code that's still being generated."""

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.clj', delete=False) as f:
        f.write(partial_code_string)
        temp_file = f.name

    try:
        # Use tree-sitter (handles incomplete code)
        result = validate_tree_sitter(temp_file)

        # Interpret results for partial code
        if result["findings"]:
            # Check if errors are "expected" for incomplete code
            incomplete_errors = [
                "unexpected-eof",
                "missing expected node",
                "parse error"
            ]

            serious_errors = [
                e for e in result["findings"]
                if not any(ie in e["message"].lower() for ie in incomplete_errors)
            ]

            if serious_errors:
                return {
                    "status": "invalid",
                    "errors": serious_errors,
                    "message": "Structural errors beyond incompleteness"
                }
            else:
                return {
                    "status": "incomplete",
                    "errors": result["findings"],
                    "message": "Code incomplete but structurally valid so far"
                }
        else:
            return {
                "status": "valid",
                "errors": [],
                "message": "Code is complete and valid"
            }

    finally:
        os.unlink(temp_file)
```

### 3. Error Ranking for LLM Attention

Prioritize which errors LLM should fix first:

```python
def rank_errors_for_llm(errors):
    """Rank errors by priority for LLM fixing."""

    priority_map = {
        "error": 3,
        "warning": 2,
        "info": 1
    }

    # Sort by priority, then by line number
    ranked = sorted(
        errors,
        key=lambda e: (
            -priority_map.get(e["severity"], 0),  # Higher priority first
            e.get("line", 0),                     # Earlier lines first
            e.get("col", 0)                       # Earlier columns first
        )
    )

    return ranked
```

### 4. Diff-Based Validation

Validate that LLM edits preserve intent:

```python
def validate_edit_preserves_structure(original_file, edited_file):
    """Use difftastic to ensure structural preservation."""

    result = subprocess.run(
        ["difft", "--format", "json", original_file, edited_file],
        capture_output=True,
        text=True
    )

    diff_data = json.loads(result.stdout)

    # Analyze structural changes
    changes = analyze_ast_diff(diff_data)

    if changes["deleted_functions"]:
        return {
            "valid": False,
            "reason": f"Functions deleted: {changes['deleted_functions']}"
        }

    if changes["major_structural_changes"]:
        return {
            "valid": False,
            "reason": "Major structural changes detected"
        }

    return {"valid": True, "changes": changes}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Lisp Validation

on: [push, pull_request]

jobs:
  validate-clojure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install clj-kondo
        run: |
          curl -sLO https://raw.githubusercontent.com/borkdude/clj-kondo/master/script/install-clj-kondo
          chmod +x install-clj-kondo
          ./install-clj-kondo

      - name: Run validation
        run: |
          python3 lisp-validator/scripts/validate_clojure.py src/ > results.json
          cat results.json

      - name: Check results
        run: |
          ERRORS=$(jq '.summary.total_errors' results.json)
          if [ "$ERRORS" -gt 0 ]; then
            echo "❌ Found $ERRORS errors"
            jq -r '.findings[] | "\(.file):\(.line):\(.col): [\(.severity)] \(.message)"' results.json
            exit 1
          fi
          echo "✅ Validation passed"

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: validation-results
          path: results.json
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Validate staged Clojure files
STAGED_CLJ=$(git diff --cached --name-only --diff-filter=ACM | grep '\.clj$')

if [ -n "$STAGED_CLJ" ]; then
    echo "Validating Clojure files..."

    for file in $STAGED_CLJ; do
        python3 scripts/validate_clojure.py "$file" --no-joker > /dev/null

        if [ $? -ne 0 ]; then
            echo "❌ Validation failed for $file"
            python3 scripts/validate_clojure.py "$file" --format text
            exit 1
        fi
    done

    echo "✅ All Clojure files validated"
fi

exit 0
```

## Performance Optimization

### Parallel Validation

For large projects, validate files in parallel:

```python
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def validate_project_parallel(project_dir, dialect="clojure"):
    """Validate all files in parallel."""

    # Find all relevant files
    extensions = {
        "clojure": [".clj", ".cljs", ".cljc"],
        "racket": [".rkt"],
        "common-lisp": [".lisp", ".cl", ".asd"]
    }

    files = []
    for ext in extensions.get(dialect, []):
        files.extend(Path(project_dir).rglob(f"*{ext}"))

    # Validate in parallel
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(validate_file, files))

    # Aggregate results
    all_errors = []
    for result in results:
        all_errors.extend(result.get("findings", []))

    return {
        "total_files": len(files),
        "total_errors": len(all_errors),
        "errors": all_errors
    }
```

### Caching Strategies

Use tool-specific caching when available:

**clj-kondo:**
```bash
# First run creates .clj-kondo/ cache
clj-kondo --lint src/

# Subsequent runs use cache (much faster)
clj-kondo --lint src/
```

**raco warn:**
```bash
# Incremental validation
raco warn --incremental src/
```

## Error Recovery Strategies

### Auto-Fix When Safe

Only auto-fix formatting issues, never logic errors:

```python
def auto_fix_if_safe(file_path, validation_result):
    """Auto-fix only formatting issues."""

    errors = validation_result["findings"]

    # Check if all errors are formatting-related
    formatting_types = [
        "whitespace",
        "indentation",
        "trailing-whitespace",
        "missing-whitespace"
    ]

    all_formatting = all(
        any(ft in e.get("type", "").lower() for ft in formatting_types)
        for e in errors
    )

    if all_formatting:
        # Safe to auto-fix
        apply_formatter(file_path)
        return {"fixed": True, "method": "auto-format"}
    else:
        # Requires manual intervention
        return {"fixed": False, "reason": "Non-formatting errors present"}
```

### Graceful Degradation

When primary tools aren't available, fall back gracefully:

```python
def validate_with_fallback(file_path):
    """Try multiple validators with fallbacks."""

    # Try primary tool
    if check_tool_available("clj-kondo"):
        return validate_clojure(file_path)

    # Fallback to secondary
    if check_tool_available("joker"):
        return validate_joker(file_path)

    # Last resort: tree-sitter
    if check_tool_available("tree-sitter"):
        return validate_tree_sitter(file_path)

    # No tools available
    return {
        "error": "No validation tools available",
        "recommendation": "Install clj-kondo, joker, or tree-sitter"
    }
```

## Best Practices Summary

1. **Use structured output** (JSON) when possible
2. **Validate incrementally** after each LLM edit
3. **Handle incomplete code** with tree-sitter
4. **Separate validation from fixing**
5. **Rank errors by priority** for LLM attention
6. **Cache validation results** for performance
7. **Run tools in parallel** for large projects
8. **Provide clear feedback** to LLM with file:line:col
9. **Use exit codes** for automation
10. **Fall back gracefully** when tools unavailable
