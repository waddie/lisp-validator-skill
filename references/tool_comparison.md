# Tool Comparison Matrix

**Purpose:** This reference document provides a comprehensive comparison of all available Lisp validation tools across dialects, helping you select the optimal tools for your validation needs.

**When to load this file:**
- Selecting validation tools for a new project
- Understanding capabilities and limitations of each tool
- Determining optimal tool combinations for your workflow
- Setting up CI/CD validation pipelines
- Troubleshooting tool-specific issues

**What's inside:**
- Quick reference comparison table
- Detailed profiles for each tool (installation, usage, output formats)
- Dialect-specific recommendations
- Performance benchmarks
- Exit code standards
- Optimal tool combinations for LLM workflows

## Quick Reference Table

| Tool | Dialect | Installation | Detection | Auto-fix | JSON Output | Incomplete Code | Active 2020-2025 | LLM Integration |
|------|---------|-------------|-----------|----------|-------------|-----------------|------------------|--------------------|
| **clj-kondo** | Clojure | brew/npm/binary | Excellent | No | Yes (JSON/EDN) | Partial | Yes | ⭐⭐⭐⭐⭐ |
| **joker** | Clojure | brew/binary | Good | No | No (parseable) | No | Yes | ⭐⭐⭐⭐ |
| **raco review** | Racket | raco pkg | Excellent | No | No (structured) | No | Yes | ⭐⭐⭐⭐ |
| **raco warn** | Racket | raco pkg | Excellent | No | No | No | Yes | ⭐⭐⭐⭐ |
| **raco fix** | Racket | raco pkg | Good | Yes | No | No | Yes | ⭐⭐⭐⭐ |
| **raco fmt** | Racket | raco pkg | No | Yes | No | No | Yes | ⭐⭐⭐ |
| **SBLint** | Common Lisp | roswell | Excellent | No | No (structured) | Partial | Yes | ⭐⭐⭐⭐ |
| **Mallet** | Common Lisp | binary | Good | No | No | Partial | Yes (new) | ⭐⭐⭐ |
| **SBCL** | Common Lisp | brew/apt | Excellent | No | No | No | Yes | ⭐⭐⭐ |
| **tree-sitter** | Multi-dialect | npm | Excellent | No | Yes (via tools) | Yes | Yes | ⭐⭐⭐⭐⭐ |
| **difftastic** | Multi-dialect | cargo/brew | Excellent | No | Yes | Yes | Yes | ⭐⭐⭐⭐⭐ |
| **scmindent** | Universal | raco pkg | No | Yes (indent) | No | Yes | Yes | ⭐⭐⭐ |
| **cljfmt** | Clojure | clj tools | Indirect | Yes | No | No | Yes | ⭐⭐ |

## Detailed Tool Profiles

### Clojure Tools

#### clj-kondo (Primary Validator)

**Strengths:**
- Machine-readable JSON/EDN output perfect for LLM parsing
- Comprehensive error detection (syntax, semantics, style)
- Fast execution (< 100ms typical)
- Incremental analysis via caching (`.clj-kondo/`)
- Cross-file namespace analysis
- No REPL required (static analysis)

**Weaknesses:**
- Detection-only (no auto-fix)
- May not catch all errors that joker finds (different heuristics)

**Installation:**
```bash
# macOS/Linux
brew install borkdude/brew/clj-kondo

# Universal (Node.js)
npm install -g clj-kondo

# Binary download
# https://github.com/borkdude/clj-kondo/releases
```

**Usage:**
```bash
# JSON output
clj-kondo --lint src/ --config '{:output {:format :json}}'

# Stdin
echo '(defn foo {)' | clj-kondo --lint -

# Exit codes: 0=success, 2=warnings, 3=errors
```

**Output Format:**
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
  "summary": {
    "error": 1,
    "warning": 2,
    "info": 0,
    "duration": 25,
    "files": 10
  }
}
```

#### joker (Secondary Validator)

**Strengths:**
- Catches different errors than clj-kondo (complementary)
- Lightweight Go binary
- Fast execution
- Can format code (`--format`)

**Weaknesses:**
- No JSON output (parseable text only)
- One file at a time
- May have false positives on macro-introduced bindings
- No cross-file analysis

**Installation:**
```bash
brew install candid82/joker/joker
# Or download from https://github.com/candid82/joker/releases
```

**Usage:**
```bash
# Lint file
joker --lint foo.clj

# Stdin
echo '[{:a 1' | joker --lint -

# Specify dialect
joker --lint --dialect cljs foo.cljs
```

**Output Format:**
```
<filename>:<line>:<column>: <issue type>: <message>
```

### Racket/Scheme Tools

#### raco expand (Safe Syntax Check)

**Strengths:**
- Validates syntax without execution (safe)
- Clear error messages with location
- Fast
- Included with Racket

**Weaknesses:**
- Detection-only
- Requires readable code

**Usage:**
```bash
# File
raco expand file.rkt

# Stdin
raco expand --
```

**Output Format:**
```
file:line:column: message
```

#### raco review (Fast Linting)

**Strengths:**
- Very fast (no expansion overhead)
- Structured output (file:line:col:level:message)
- Flycheck integration available
- Error suppression via comments

**Weaknesses:**
- Surface-level only (no deep analysis)
- Requires installation (`raco pkg install review`)

**Usage:**
```bash
raco review filename.rkt
```

**Output Format:**
```
filename.rkt:5:10:error: identifier is already defined
```

#### raco warn (Comprehensive Analysis)

**Strengths:**
- Package-level analysis
- Sophisticated cross-namespace checking
- Provides suggestions
- Incremental validation support

**Weaknesses:**
- Slower than review
- Requires installation (`raco pkg install syntax-warn`)

**Usage:**
```bash
# File
raco warn file.rkt

# Package
raco warn -p package-name

# Suppress specific warnings
raco warn --suppress unused-identifier
```

**Output Format:**
```
file.rkt:12:4:warning: identifier 'x' is never used
  (define x 10)
  suggestion: remove unused binding
```

#### raco fix (Auto-Repair)

**Strengths:**
- Automatic corrections with conflict resolution
- Dry run preview mode
- Per-module configuration

**Weaknesses:**
- Limited to fixable warnings
- Requires installation

**Usage:**
```bash
# Dry run (preview)
raco fix file.rkt

# Apply changes
raco fix -E file.rkt
```

### Common Lisp Tools

#### SBLint (Primary Linter)

**Strengths:**
- Machine-readable output (file:line:col: message)
- Fast execution
- CI/CD friendly
- Reviewdog integration
- Active maintenance

**Weaknesses:**
- Requires Roswell installation
- SBCL-specific
- Loads ASDF systems (may have side effects)
- Cannot process severely incomplete code

**Installation:**
```bash
ros install sbcl
ros use sbcl
ros install cxxxr/sblint
```

**Usage:**
```bash
# All ASD files
sblint

# Specific files
sblint src/main.lisp

# Recursive
sblint src/
```

**Output Format:**
```
file:line:col: message
```

#### SBCL (Compiler Validation)

**Strengths:**
- Deep semantic analysis
- Detailed error messages with line/column
- Excellent error detection
- Multiple severity levels (ERROR, WARNING, STYLE-WARNING, NOTE)

**Weaknesses:**
- Requires full Lisp runtime
- Verbose output (not machine-parseable)
- May execute code during loading (security concern)
- Slower than dedicated linters

**Installation:**
```bash
# macOS
brew install sbcl

# Linux
apt install sbcl

# Roswell
ros install sbcl
```

**Usage:**
```bash
# Load and compile
sbcl --noinform --disable-debugger --load myfile.lisp --quit

# Explicit compile
sbcl --noinform --eval "(compile-file \"myfile.lisp\")" --eval "(quit)"
```

**Output Format:**
```
READ error during COMPILE-FILE: unmatched close parenthesis
  Line: 64, Column: 23, File-Position: 237
```

### Universal Tools

#### tree-sitter (Incomplete Code Parser)

**Strengths:**
- **Best support for incomplete code** (critical for LLM workflows)
- Incremental parsing
- Multiple language grammars available
- Machine-readable parse tree
- Python/Rust/JavaScript APIs
- ERROR nodes mark problem areas

**Weaknesses:**
- Requires grammar installation
- CLI version 0.20+ has compatibility issues (use 0.19.3)
- Less sophisticated than dialect-specific tools

**Installation:**
```bash
# CLI
npm install -g tree-sitter-cli@0.19.3

# Python
pip install tree-sitter tree-sitter-commonlisp tree-sitter-clojure tree-sitter-elisp

# Rust
cargo add tree-sitter tree-sitter-grammars
```

**Usage:**
```bash
# Parse and visualize
tree-sitter parse file.lisp

# Run tests
tree-sitter test
```

**Output:**
- Parse tree with ERROR nodes marking failures
- MISSING nodes for expected tokens

#### difftastic (Structural Diffing)

**Strengths:**
- AST-based diffing (ignores formatting)
- Handles incomplete code via tree-sitter
- JSON output mode (machine-readable)
- Excellent for validating code changes
- Git integration
- 30+ languages supported

**Weaknesses:**
- Can be slow on large files
- Primarily a diff tool, not validator

**Installation:**
```bash
cargo install difftastic
# Or via package manager
```

**Usage:**
```bash
# Basic diff
difft file1.lisp file2.lisp

# Side-by-side
difft --display side-by-side file1.lisp file2.lisp

# JSON output
difft --format json file1.lisp file2.lisp
```

## Dialect-Specific Recommendations

### For Clojure Projects
1. **Primary:** clj-kondo (JSON output, comprehensive)
2. **Secondary:** joker (complementary checks)
3. **Fallback:** tree-sitter (incomplete code)

**Optimal Pipeline:**
```bash
clj-kondo --lint src/ --config '{:output {:format :json}}' > results.json
joker --lint src/**/*.clj 2> joker-results.txt
```

### For Racket/Scheme Projects
1. **Fast check:** raco expand (safe syntax)
2. **Surface lint:** raco review (quick)
3. **Deep analysis:** raco warn (comprehensive)
4. **Auto-fix:** raco fmt (formatting)
5. **Fallback:** tree-sitter (incomplete code)

**Optimal Pipeline:**
```bash
raco expand file.rkt > /dev/null
raco review file.rkt
raco warn file.rkt
raco fmt -i file.rkt  # If validation passes
```

### For Common Lisp Projects
1. **Primary:** SBLint (machine-readable)
2. **Deep validation:** SBCL (semantic analysis)
3. **Fallback:** tree-sitter (incomplete code)

**Optimal Pipeline:**
```bash
sblint src/
sbcl --noinform --disable-debugger --load file.lisp --quit
```

### For Incomplete/Partial Code
1. **Primary:** tree-sitter (handles incomplete)
2. **Alternative:** difftastic (structural validation)

## Exit Code Standards

| Tool | 0 (Success) | 1 (General Error) | 2 (Warnings) | 3 (Errors) |
|------|------------|-------------------|--------------|------------|
| clj-kondo | No issues | - | Warnings only | Errors present |
| joker | No issues | Failure | - | Issues present |
| raco tools | No warnings | - | - | Non-zero for issues |
| SBLint | No issues | Failure | - | Issues present |
| tree-sitter | Parse success | - | - | Parse failure |

## Performance Comparison

| Tool | Typical Speed | Project Scale | Caching |
|------|--------------|---------------|---------|
| clj-kondo | < 100ms | Large | Yes (`.clj-kondo/`) |
| joker | < 50ms per file | Medium | No |
| raco review | Very fast | Large | No |
| raco warn | Moderate | Large | Incremental |
| SBLint | Fast | Large | No |
| SBCL | Slow | Medium | No |
| tree-sitter | Fast | Large | Incremental |

## Tool Combinations

### Optimal for LLM Workflows

**Clojure:**
- clj-kondo (JSON) + tree-sitter (incomplete)
- Parse JSON for structured errors
- Fallback to tree-sitter for partial expressions

**Racket:**
- raco expand + raco review + tree-sitter (incomplete)
- Chain for progressive validation
- tree-sitter for partial code

**Common Lisp:**
- SBLint + tree-sitter (incomplete)
- SBLint for complete files
- tree-sitter for partial code

### CI/CD Integration

**Clojure:**
```yaml
- clj-kondo --lint src/ --config '{:output {:format :json}}' | jq
- test $(jq '.summary.error' results.json) -eq 0
```

**Racket:**
```bash
raco expand src/main.rkt && raco review src/ && raco warn -p my-package
```

**Common Lisp:**
```bash
sblint src/ || exit 1
```
