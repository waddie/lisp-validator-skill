# System Architecture

**When to load this file:**
- Understanding the overall system design
- Debugging validation workflows
- Adding new dialects or tools
- Modifying the orchestration logic

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     User/LLM Input                             │
│                  (file/directory path)                         │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
                  ┌───────────────┐
                  │ validate.py   │
                  │ (Orchestrator)│
                  └──────┬────────┘
                         │
         ┌───────────────┼───────────────┬────────────────┐
         │               │               │                │
         ▼               ▼               ▼                ▼
   ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌──────────┐
   │validate_ │  │validate_ │  │validate_common│  │validate_ │
   │clojure.py│  │scheme.py │  │   _lisp.py    │  │tree_     │
   │          │  │          │  │               │  │sitter.py │
   └────┬─────┘  └────┬─────┘  └───────┬───────┘  └────┬─────┘
        │             │                │               │
        ▼             ▼                ▼               ▼
   ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌──────────┐
   │clj-kondo │  │  raco    │  │    SBLint     │  │tree-     │
   │  joker   │  │  tools   │  │     SBCL      │  │sitter    │
   └──────────┘  └──────────┘  └───────────────┘  │(Python   │
                                                  │ or CLI)  │
                                                  └──────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Unified JSON Output │
              │  {findings, summary} │
              └──────────────────────┘
```

## Component Responsibilities

### Orchestrator Layer

**validate.py** - Main entry point
- Validates input path existence
- Auto-detects dialect from file extension/content
- Routes to appropriate dialect validator
- Handles `--tree-sitter` and `--dialect` flags
- Normalizes output format (JSON/text/summary)
- Returns unified result structure

### Dialect Validator Layer

Each dialect-specific validator follows the same pattern:

**validate_clojure.py**
- Runs clj-kondo (primary tool)
- Runs joker (optional secondary tool)
- Normalizes findings to unified schema
- Deduplicates errors across tools
- Returns ValidationResult dict

**validate_scheme.py**
- Runs raco expand (syntax check)
- Runs raco review (surface lint)
- Runs raco warn (deep analysis)
- Falls back to dialect-specific Scheme if raco unavailable
- Returns ValidationResult dict

**validate_common_lisp.py**
- Runs SBLint (machine-readable output)
- Runs SBCL (deep semantic validation, optional)
- Parses SBCL's verbose output
- Returns ValidationResult dict

**validate_tree_sitter.py**
- Tries Python library first (more reliable)
- Falls back to CLI if library unavailable
- Detects appropriate grammar
- Extracts ERROR and MISSING nodes
- Returns ValidationResult dict

### Tool Layer

External validation tools (not part of this codebase):
- **clj-kondo**: Clojure linter with JSON output
- **joker**: Lightweight Clojure linter
- **raco**: Racket command-line tools
- **SBLint**: Common Lisp linter
- **SBCL**: Common Lisp compiler
- **tree-sitter**: Universal parser (Python lib or CLI)

### Shared Modules

**validation_types.py**
- TypedDict definitions (Finding, ValidationResult, ValidationSummary)
- Constants (timeout values, exit codes, dialect names)
- Helper functions (error factories, result builders)

**check_tools.py**
- Detects available validation tools
- Provides platform-specific installation commands
- Generates recommendations based on available tools

## Data Flow

### 1. Input Processing

```python
# User provides path
target = "src/core.clj"

# validate.py checks existence
if not Path(target).exists():
    return error_result("Target not found")

# Auto-detect dialect
dialect = detect_dialect(target)  # Returns "clojure"
```

### 2. Routing

```python
# Route to dialect-specific validator
if dialect == DIALECT_CLOJURE:
    result = validate_clojure(target)
elif dialect == DIALECT_RACKET:
    result = validate_scheme(target)
# ... etc
```

### 3. Multi-Tool Validation

```python
# Example: validate_clojure.py

# Run primary tool
kondo_result = run_clj_kondo(target)
findings = normalize_clj_kondo_findings(kondo_result["findings"])

# Run secondary tool
joker_errors = run_joker(target)

# Deduplicate by (file, line, col)
existing = {(f["file"], f["line"], f["col"]) for f in findings}
for error in joker_errors:
    location = (error["file"], error["line"], error["col"])
    if location not in existing:
        findings.append(error)
```

### 4. Output Normalization

```python
# All validators return this structure
{
    "target": str,
    "dialect": str,
    "findings": [
        {
            "file": str,
            "line": int,
            "col": int,
            "severity": "error" | "warning" | "info",
            "message": str,
            "tool": str
        }
    ],
    "summary": {
        "total_errors": int,
        "total_warnings": int,
        "tools_used": [str]
    }
}
```

### 5. Format Conversion

```python
# validate.py handles output formatting
result = validate(target)
output = format_output(result, output_format="text")
print(output)
```

## Error Handling Strategy

### Graceful Degradation

When a tool is not found:
1. Add warning to `result["warnings"]`
2. Continue with available tools
3. Return partial results rather than failing

```python
try:
    kondo_result = run_clj_kondo(target)
except FileNotFoundError:
    result["warnings"].append("clj-kondo not found")
    # Continue with joker if available
```

### Timeout Protection

All subprocess calls have timeouts:
```python
subprocess.run(
    command,
    timeout=CLJ_KONDO_TIMEOUT_SECONDS  # 30 seconds
)
```

### Output Parsing Failures

If tool output cannot be parsed:
1. Log the error in warnings
2. Return empty findings for that tool
3. Don't fail entire validation

## Extension Points

### Adding a New Dialect

1. Create `scripts/validate_<dialect>.py`
2. Implement `validate_<dialect>(target: str) -> ValidationResult`
3. Add dialect detection in `validate.py`:
   - Update `detect_dialect_from_extension()`
   - Update `detect_dialect_from_content()`
4. Add routing in `validate()` function
5. Add constants to `validation_types.py`
6. Update documentation

### Adding a New Tool

1. Create `run_<tool>(target: str)` function
2. Create `parse_<tool>_output(output: str)` function
3. Integrate in relevant dialect validator
4. Add deduplication logic
5. Update `check_tools.py` with detection
6. Add timeout constant to `validation_types.py`

## Performance Considerations

### Caching

Some tools support caching:
- clj-kondo: `.clj-kondo/` directory
- raco warn: incremental analysis

### Parallel Validation

For large projects, validators can be run in parallel:
```bash
find src -name '*.clj' | xargs -P 4 -I {} python3 scripts/validate.py {}
```

### Tool Selection

Use `--no-joker` or `--no-sbcl` to skip secondary tools for faster validation.

## Security Considerations

### Input Validation

- File paths are validated before processing
- No shell injection (subprocess uses list, not string)
- Timeouts prevent resource exhaustion

### Tool Execution

- Some tools (SBCL) may execute code during loading
- Validators use `--noinform --disable-debugger --quit` flags to minimize risk
- Tree-sitter is safe (parsing only, no execution)

## Testing Strategy

When modifying the architecture:

1. **Unit tests**: Test each validator independently
2. **Integration tests**: Test orchestrator routing
3. **Tool availability tests**: Test graceful degradation
4. **Deduplication tests**: Verify findings aren't duplicated
5. **Format tests**: Verify all output formats work
6. **Exit code tests**: Verify correct codes (0/2/3)
