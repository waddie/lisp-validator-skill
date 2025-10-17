# Error Pattern Reference

**Purpose:** This reference document provides regex patterns and parsing strategies for extracting structured error information from each Lisp validation tool's output format.

**When to load this file:**
- Parsing validation tool output programmatically
- Normalizing errors from multiple tools to a unified schema
- Implementing custom error handlers or formatters
- Debugging parsing issues with tool output
- Understanding tool-specific output formats

**What's inside:**
- Regex patterns for structured output (clj-kondo JSON, raco review, SBLint)
- Parsing strategies for unstructured output (SBCL, Scheme dialects)
- Unified error schema for normalization
- Common error types by dialect
- Edge cases and parsing best practices
- Complete universal parser example

## Structured Output Formats

### clj-kondo (JSON)

**Format:** Fully structured JSON

**Example:**
```json
{
  "findings": [{
    "type": "unexpected-eof",
    "filename": "src/calc.clj",
    "row": 10,
    "col": 15,
    "end-row": 10,
    "end-col": 20,
    "level": "error",
    "message": "Unexpected EOF."
  }],
  "summary": {"error": 1, "warning": 2}
}
```

**Parsing:** Use JSON parser, no regex needed

**Python Example:**
```python
import json
result = json.loads(output)
for finding in result["findings"]:
    print(f"{finding['filename']}:{finding['row']}:{finding['col']}: {finding['message']}")
```

**Key Fields:**
- `filename`: Source file path
- `row`: Line number (1-indexed)
- `col`: Column number (1-indexed)
- `end-row`, `end-col`: End position
- `level`: "error" | "warning" | "info"
- `type`: Error type identifier
- `message`: Human-readable description

### joker (Parseable Text)

**Format:** `<filename>:<line>:<column>: <issue type>: <message>`

**Regex Pattern:**
```python
pattern = r'(.+?):(\d+):(\d+):\s*(.+?):\s*(.+)'
```

**Example:**
```
<stdin>:1:1: Read error: Unexpected EOF
foo.clj:12:5: Parse warning: unused binding: x
```

**Parsing Example:**
```python
import re
pattern = r'(.+?):(\d+):(\d+):\s*(.+?):\s*(.+)'
match = re.match(pattern, line)
if match:
    filename, line_num, col, issue_type, message = match.groups()
    severity = "error" if "error" in issue_type.lower() else "warning"
```

**Issue Types:**
- `Read error`: Syntax/parsing errors
- `Parse error`: Semantic errors
- `Parse warning`: Warnings
- `Exception`: Runtime errors during analysis

### raco review/warn (Structured Text)

**Format:** `filename:line:col:level:message`

**Regex Pattern:**
```python
pattern = r'(.+?):(\d+):(\d+):(error|warning|info):\s*(.+)'
```

**Example:**
```
filename.rkt:5:10:error: identifier is already defined
file.rkt:12:4:warning: identifier 'x' is never used
```

**With Suggestions (raco warn):**
```
file.rkt:12:4:warning: identifier 'x' is never used
  (define x 10)
  suggestion: remove unused binding
```

**Parsing Example:**
```python
pattern = r'(.+?):(\d+):(\d+):(warning|error|info):\s*(.+?)(?:\s+suggestion:\s*(.+))?$'
match = re.match(pattern, line)
if match:
    file, line_num, col, level, message, suggestion = match.groups()
```

### raco expand (Basic Error)

**Format:** `file:line:column: message`

**Regex Pattern:**
```python
pattern = r'(.+?):(\d+):(\d+):\s*(.+)'
```

**Example:**
```
file.rkt:3:4: unbound identifier at: foo
```

### SBLint (Machine-Readable)

**Format:** `file:line:col: message`

**Regex Pattern:**
```python
pattern = r'(.+?):(\d+):(\d+):\s*(.+)'
```

**Example:**
```
test.lisp:1:0: The variable A is defined but never used.
src/main.lisp:45:12: undefined variable: FOO
```

**Severity Detection:**
Infer from message keywords:
- Error: "error", "undefined", "unbound"
- Warning: "warning", "style-warning", "never used"
- Info: other

**Parsing Example:**
```python
match = re.match(r'(.+?):(\d+):(\d+):\s*(.+)', line)
if match:
    file, line_num, col, message = match.groups()
    # Infer severity
    if any(word in message.lower() for word in ["error", "undefined", "unbound"]):
        severity = "error"
    elif "warning" in message.lower():
        severity = "warning"
    else:
        severity = "info"
```

## Unstructured Output Formats

### SBCL (Verbose Multi-Line)

**Format:** Multi-line with various patterns

**Pattern 1 - Line/Column:**
```
READ error during COMPILE-FILE: unmatched close parenthesis
  Line: 64, Column: 23, File-Position: 237
```

**Regex:**
```python
line_col_pattern = r'Line:\s*(\d+),\s*Column:\s*(\d+)'
```

**Pattern 2 - Character Position:**
```
debugger invoked on a SB-C::INPUT-ERROR-IN-COMPILE-FILE:
  READ failure in COMPILE-FILE
    at character 477: end of file
```

**Regex:**
```python
char_pattern = r'at character\s+(\d+)'
```

**Severity Indicators:**
- `ERROR`, `debugger invoked` → error
- `WARNING` → warning
- `STYLE-WARNING` → info
- `NOTE` → info

**Parsing Strategy:**
1. Split output into logical blocks by error keywords
2. Extract line/column from each block
3. Clean verbose SBCL-specific text
4. Truncate very long messages

**Example:**
```python
def parse_sbcl_output(output):
    errors = []
    current_error = None
    current_lines = []

    for line in output.split('\n'):
        if any(kw in line for kw in ["ERROR", "WARNING", "debugger invoked"]):
            if current_error:
                # Process previous error
                error_text = ' '.join(current_lines)
                errors.append(parse_sbcl_block(error_text))

            # Start new error
            current_error = determine_severity(line)
            current_lines = [line]
        elif current_error:
            current_lines.append(line)

    if current_error:
        errors.append(parse_sbcl_block(' '.join(current_lines)))

    return errors
```

### Scheme Dialects (Conversational)

#### Guile

**Format:** Stack traces with context

**Example:**
```
ice-9/boot-9.scm:1685:16: In procedure raise-exception:
Unbound variable: foo
```

**Pattern:**
```python
pattern = r'(.+?):(\d+):(\d+):\s*In procedure\s+.+?:\s*(.+)'
```

#### Chez

**Format:** Descriptive with limited location info

**Example:**
```
Exception: variable foo is not bound
Type (debug) to enter the debugger.
```

**Strategy:** Extract error type and message, location often absent

#### MIT Scheme

**Format:** Interactive continuation-style

**Example:**
```
;Unbound variable: foo
;To continue, call RESTART with an option number:
; (RESTART 3) => Specify a value to use instead of foo.
```

**Strategy:** Extract first line after `;`, ignore continuation options

### tree-sitter (Parse Tree)

**Format:** Parse tree with ERROR/MISSING nodes

**CLI Output Pattern:**
```
ERROR [row, col] - [row, col]
MISSING <node-type> [row, col]
```

**Regex:**
```python
error_pattern = r'ERROR\s+\[(\d+),\s*(\d+)\]\s*-\s*\[(\d+),\s*(\d+)\]'
missing_pattern = r'MISSING\s+(.+?)\s+\[(\d+),\s*(\d+)\]'
```

**Python Library (Preferred):**
```python
from tree_sitter import Parser

tree = parser.parse(source_code)

def extract_errors(node):
    errors = []
    if node.type == "ERROR":
        errors.append({
            "line": node.start_point[0] + 1,
            "col": node.start_point[1] + 1,
            "end_line": node.end_point[0] + 1,
            "end_col": node.end_point[1] + 1,
            "message": "Parse error"
        })
    for child in node.children:
        errors.extend(extract_errors(child))
    return errors
```

## Unified Error Schema

For consistent LLM integration, normalize all errors to this schema:

```python
{
    "file": str,           # Source file path
    "line": int,           # Line number (1-indexed)
    "col": int,            # Column number (1-indexed)
    "end_line": int,       # Optional end line
    "end_col": int,        # Optional end column
    "severity": str,       # "error" | "warning" | "info"
    "message": str,        # Human-readable description
    "type": str,           # Optional error type/code
    "tool": str,           # Tool that found the error
    "suggestion": str      # Optional fix suggestion
}
```

## Common Error Types by Dialect

### Clojure (clj-kondo)

**Type Identifiers:**
- `unexpected-eof`: Missing closing delimiter
- `unmatched-delimiter`: Wrong closing bracket/paren/brace
- `unresolved-symbol`: Symbol not found
- `invalid-arity`: Wrong number of arguments
- `unused-binding`: Unused let/fn parameter
- `redefined-var`: Duplicate definition

### Racket (raco)

**Error Categories:**
- `unbound identifier`: Variable not defined
- `arity mismatch`: Wrong argument count
- `duplicate binding`: Same name defined twice
- `syntax error`: Parse/read error
- `type error`: Type mismatch (Typed Racket)

### Common Lisp (SBLint/SBCL)

**Warning Categories:**
- `undefined variable`: Symbol not bound
- `undefined function`: Function not defined
- `unused variable`: Binding never referenced
- `style-warning`: Coding style issue
- `READ error`: Syntax/parse error

### tree-sitter

**Node Types:**
- `ERROR`: Unparseable section
- `MISSING`: Expected token absent
- Parse tree structure indicates location

## Edge Cases

### Multi-Line Errors

**SBCL Example:**
```
ERROR during compilation:
  Multiple problems detected:
    Line 10: unbalanced parentheses
    Line 15: undefined symbol
```

**Strategy:** Parse each problem line separately, associate with same file

### Context Lines

**raco warn Example:**
```
file.rkt:12:4:warning: identifier 'x' is never used
  (define x 10)
  suggestion: remove unused binding
```

**Strategy:** Capture main error line, optionally store context/suggestion

### Relative vs Absolute Paths

**Different tools use different path formats:**
- Absolute: `/Users/name/project/src/file.clj`
- Relative: `src/file.clj`
- Stdin: `<stdin>` or `-`

**Normalization:**
```python
from pathlib import Path

def normalize_path(path_str, base_dir="."):
    if path_str in ("<stdin>", "-"):
        return "<stdin>"

    path = Path(path_str)
    if path.is_absolute():
        return str(path)
    else:
        return str((Path(base_dir) / path).resolve())
```

### Zero-Indexing vs One-Indexing

**tree-sitter uses 0-indexed positions:**
```python
# tree-sitter output
line = node.start_point[0] + 1  # Convert to 1-indexed
col = node.start_point[1] + 1
```

**Most other tools use 1-indexed**

## Parsing Best Practices

1. **Try structured formats first** (JSON, parseable patterns)
2. **Use regex for semi-structured text** (file:line:col patterns)
3. **Block-based parsing for verbose output** (SBCL, Scheme)
4. **Normalize to unified schema** for LLM consumption
5. **Preserve tool identity** (`tool` field) for debugging
6. **Handle missing location info** (default to line 0, col 0)
7. **Infer severity from keywords** when not explicit
8. **Deduplicate errors** from multiple tools (same file:line:col)

## Example: Universal Parser

```python
def parse_error_line(line, tool):
    """Universal error line parser with fallbacks."""

    # Try structured formats
    patterns = [
        # file:line:col:level:message (raco, sblint)
        r'(.+?):(\d+):(\d+):(\w+):\s*(.+)',
        # file:line:col: message (basic)
        r'(.+?):(\d+):(\d+):\s*(.+)',
        # file:line: message (no column)
        r'(.+?):(\d+):\s*(.+)',
    ]

    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            groups = match.groups()
            if len(groups) == 5:
                file, line, col, level, msg = groups
                return {
                    "file": file,
                    "line": int(line),
                    "col": int(col),
                    "severity": level,
                    "message": msg,
                    "tool": tool
                }
            elif len(groups) == 4:
                file, line, col, msg = groups
                return {
                    "file": file,
                    "line": int(line),
                    "col": int(col),
                    "severity": infer_severity(msg),
                    "message": msg,
                    "tool": tool
                }
            elif len(groups) == 3:
                file, line, msg = groups
                return {
                    "file": file,
                    "line": int(line),
                    "col": 0,
                    "severity": infer_severity(msg),
                    "message": msg,
                    "tool": tool
                }

    return None

def infer_severity(message):
    """Infer severity from message keywords."""
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ["error", "undefined", "unbound", "unmatched"]):
        return "error"
    elif any(kw in msg_lower for kw in ["warning", "unused"]):
        return "warning"
    else:
        return "info"
```
