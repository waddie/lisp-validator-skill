# Failure Modes and Recovery

**When to load this file:**
- Debugging validation failures
- Understanding error scenarios
- Implementing error recovery in automated workflows
- Troubleshooting production issues

## Overview

This document catalogs common failure modes, their causes, symptoms, and recovery strategies for the Lisp Validator skill.

## Tool Availability Failures

### Tool Not Found

**Symptom:** `clj-kondo not found` in warnings array

**Cause:**
- Tool not installed
- Tool not in PATH
- Wrong tool name/version

**Recovery:**
```python
# Check tool availability first
result = subprocess.run(["python3", "scripts/check_tools.py", "--json"], capture_output=True)
tools = json.loads(result.stdout)["tools"]

if not tools["clj-kondo"]["available"]:
    # Install or use alternate validator
    result = validate_tree_sitter(target)  # Fallback
```

**Prevention:**
- Run `check_tools.py` before validation
- Document tool requirements in CI/CD
- Use Docker with pre-installed tools

### Tool Version Incompatibility

**Symptom:** `Cannot parse output` errors

**Cause:**
- tree-sitter CLI 0.20+ has breaking changes
- clj-kondo version too old (< 2020.01.01)
- joker breaking changes in 0.14

**Recovery:**
```bash
# Downgrade to compatible version
npm uninstall -g tree-sitter-cli
npm install -g tree-sitter-cli@0.19.3

# Or use Python library instead
pip install tree-sitter tree-sitter-clojure
python3 scripts/validate_tree_sitter.py file.clj  # Uses Python lib
```

**Prevention:**
- Pin tool versions in CI/CD
- Document version requirements
- Test against multiple versions

## Parse/Timeout Failures

### Subprocess Timeout

**Symptom:** `timed out` in warnings

**Cause:**
- Very large file (> 100K LOC)
- Infinite loop in parser
- Resource exhaustion

**Recovery:**
```python
# Increase timeout for large files
import validation_types
validation_types.CLJ_KONDO_TIMEOUT_SECONDS = 60  # Double timeout

# Or validate smaller chunks
for file in files:
    try:
        result = validate_clojure(file)
    except subprocess.TimeoutExpired:
        # Skip or retry with tree-sitter
        result = validate_tree_sitter(file)
```

**Prevention:**
- Split large files before validation
- Set appropriate timeouts based on file size
- Use streaming validation for very large files

### Memory Exhaustion

**Symptom:** Process killed, no output

**Cause:**
- File too large for available memory
- Too many files validated in parallel
- Memory leak in tool

**Recovery:**
```bash
# Reduce parallelism
find src -name '*.clj' | xargs -P 2 -I {} python3 scripts/validate.py {}  # Was -P 4

# Increase memory limit (Linux)
ulimit -v 2000000  # 2GB

# Validate in batches
ls src/*.clj | split -l 10 - batch_
for batch in batch_*; do
    cat $batch | xargs python3 scripts/validate.py
done
```

**Prevention:**
- Monitor memory usage
- Validate incrementally (only changed files)
- Use caching (clj-kondo `.clj-kondo/` directory)

## Output Parsing Failures

### JSON Parsing Error

**Symptom:** `JSONDecodeError: Expecting value`

**Cause:**
- Tool output contains non-JSON prefix
- stderr mixed with stdout
- Tool crashed mid-output

**Recovery:**
```python
try:
    result = json.loads(output)
except json.JSONDecodeError:
    # Try cleaning output first
    lines = output.strip().split('\n')
    for line in lines:
        try:
            result = json.loads(line)
            break  # Found JSON
        except:
            continue
    else:
        # No valid JSON found
        result = {"error": "Cannot parse tool output", "findings": []}
```

**Prevention:**
- Capture stderr separately: `capture_output=True`
- Validate JSON before parsing
- Use tools with stable output formats (clj-kondo, SBLint)

### Malformed Tool Output

**Symptom:** Findings have missing fields

**Cause:**
- Tool output format changed
- Regex pattern mismatch
- Unexpected error message format

**Recovery:**
```python
def safe_normalize(finding):
    """Normalize finding with defaults for missing fields."""
    return {
        "file": finding.get("file", "unknown"),
        "line": finding.get("line", 0),
        "col": finding.get("col", 0),
        "severity": finding.get("severity", "error"),
        "message": finding.get("message", "Unknown error"),
        "tool": finding.get("tool", "unknown")
    }
```

**Prevention:**
- Test parsers against multiple tool versions
- Add schema validation for findings
- Log unparseable output for debugging

## File System Failures

### Target Not Found

**Symptom:** `Target not found: path/to/file.clj`

**Cause:**
- File deleted between check and validation
- Relative path not resolved correctly
- Symlink points to non-existent file

**Recovery:**
```python
# validate.py already handles this
if not Path(target).exists():
    return create_error_result(target, f"Target not found: {target}")
```

**Prevention:**
- Use absolute paths
- Validate path before starting long-running operations
- Handle race conditions in concurrent workflows

### Permission Denied

**Symptom:** `PermissionError: [Errno 13]`

**Cause:**
- File not readable
- Directory not traversable
- Tool lacks execute permission

**Recovery:**
```bash
# Fix permissions
chmod +r file.clj           # Make file readable
chmod +x scripts/*.py        # Make scripts executable

# Check permissions before validation
if [ -r "$FILE" ]; then
    python3 scripts/validate.py "$FILE"
else
    echo "Cannot read $FILE"
fi
```

**Prevention:**
- Set proper permissions in CI/CD setup
- Document permission requirements
- Use `install.sh` which sets executable bits

## Dialect Detection Failures

### Unknown Dialect

**Symptom:** `Could not auto-detect dialect, using tree-sitter fallback`

**Cause:**
- File extension not recognized (.lispy, .lsp)
- Content doesn't match heuristics
- Mixed dialect in one file

**Recovery:**
```bash
# Force specific dialect
python3 scripts/validate.py file.lsp --dialect common-lisp

# Or use tree-sitter explicitly
python3 scripts/validate.py file.lsp --tree-sitter
```

**Prevention:**
- Use standard file extensions
- Add custom detection logic to `detect_dialect_from_content()`
- Document required file extensions

### Incorrect Dialect Detection

**Symptom:** Wrong tools used (e.g., clj-kondo on Common Lisp)

**Cause:**
- File extension ambiguity (.lisp can be CL or Emacs Lisp)
- Content heuristics match wrong dialect
- Mixed code (comments from another dialect)

**Recovery:**
```bash
# Always force dialect for ambiguous files
python3 scripts/validate.py file.lisp --dialect common-lisp
```

**Prevention:**
- Use unambiguous extensions (.cl for Common Lisp, .el for Emacs Lisp)
- Add `# -*- mode: commonlisp -*-` to file headers
- Improve content detection heuristics

## Tool Integration Failures

### Deduplication Errors

**Symptom:** Same error reported multiple times

**Cause:**
- Deduplication logic broken
- Tools report different line/col for same error
- Off-by-one errors in line numbers

**Recovery:**
```python
# Fuzzy deduplication (within N lines)
FUZZ = 2  # lines
existing_ranges = []
for error in new_errors:
    loc = (error["file"], error["line"])
    if not any(f[0] == loc[0] and abs(f[1] - loc[1]) <= FUZZ for f in existing_ranges):
        findings.append(error)
        existing_ranges.append(loc)
```

**Prevention:**
- Test deduplication with multiple tools
- Use exact (file, line, col) matching first
- Add fuzzy matching only if needed

### Exit Code Confusion

**Symptom:** CI passes but validation found errors

**Cause:**
- Exit code 2 (warnings) treated as success
- Exit code 3 (errors) not checked
- Script doesn't propagate exit code

**Recovery:**
```bash
# Explicitly check exit codes
python3 scripts/validate.py src/
EXIT_CODE=$?

if [ $EXIT_CODE -eq 3 ]; then
    echo "ERRORS found - failing build"
    exit 1
elif [ $EXIT_CODE -eq 2 ]; then
    echo "WARNINGS found - build continues"
    # Decide: fail or warn
fi
```

**Prevention:**
- Document exit code meanings
- Use strict mode in CI (`set -e`)
- Test with both warnings and errors

## LLM Workflow Failures

### Incomplete Code Validation

**Symptom:** `Unexpected EOF` on incomplete but valid-so-far code

**Cause:**
- Using traditional validator on incomplete code
- tree-sitter not forced
- Expecting semantic validation on partial code

**Recovery:**
```bash
# Always use tree-sitter for incomplete code
python3 scripts/validate.py partial.clj --tree-sitter

# Ignore EOF errors for incomplete code
python3 scripts/validate.py partial.clj --tree-sitter --format json | \
    jq '.findings[] | select(.message | contains("EOF") | not)'
```

**Prevention:**
- Use `--tree-sitter` flag during LLM generation
- Switch to full validation only when code is complete
- Document incomplete code handling in workflow

### False Positives from Macros

**Symptom:** joker reports "undefined symbol" for macro-introduced bindings

**Cause:**
- joker doesn't expand macros
- clj-kondo may not recognize custom macros
- Validation without runtime context

**Recovery:**
```bash
# Use only clj-kondo (better macro support)
python3 scripts/validate_clojure.py src/ --no-joker

# Or configure clj-kondo to recognize custom macros
# Create .clj-kondo/config.edn with macro definitions
```

**Prevention:**
- Configure validators to recognize project macros
- Cross-reference multiple tools
- Document known false positives

## Recovery Patterns

### Retry with Fallback

```python
def validate_with_fallback(target):
    """Try primary validator, fall back to tree-sitter."""
    dialect = detect_dialect(target)

    try:
        if dialect == DIALECT_CLOJURE:
            return validate_clojure(target)
    except Exception as e:
        # Primary failed, try tree-sitter
        return validate_tree_sitter(target)
```

### Graceful Degradation

```python
def validate_best_effort(target):
    """Return partial results even if some tools fail."""
    result = create_empty_result(target, detect_dialect(target))

    # Try each tool, collect what we can
    for validator in [validate_clojure, validate_tree_sitter]:
        try:
            partial = validator(target)
            result["findings"].extend(partial.get("findings", []))
        except:
            continue  # Ignore failures

    return result
```

### Circuit Breaker

```python
failure_count = 0
MAX_FAILURES = 3

def validate_with_circuit_breaker(target):
    global failure_count

    if failure_count >= MAX_FAILURES:
        return {"error": "Too many failures, circuit open"}

    try:
        result = validate_clojure(target)
        failure_count = 0  # Reset on success
        return result
    except Exception:
        failure_count += 1
        raise
```

## Monitoring and Observability

### Key Metrics to Track

1. **Success rate** - % of validations that complete without errors
2. **Tool availability** - Which tools are used most often
3. **Performance** - Validation time per file size
4. **Error types** - Most common validation errors
5. **Timeout rate** - % of validations that timeout

### Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

def validate_with_logging(target):
    logger.info(f"Starting validation: {target}")

    try:
        result = validate(target)
        logger.info(f"Validation complete: {result['summary']}")
        return result
    except Exception as e:
        logger.error(f"Validation failed: {target}", exc_info=True)
        raise
```

## Summary

**Most Common Failures (in order):**
1. Tool not found (installation issue)
2. Timeout on large files
3. Incorrect dialect detection
4. JSON parsing errors
5. Permission denied

**Quick Recovery:**
- Always run `check_tools.py` first
- Use `--tree-sitter` for incomplete code
- Force `--dialect` for ambiguous files
- Increase timeouts for large files
- Fall back to alternate tools on failure
