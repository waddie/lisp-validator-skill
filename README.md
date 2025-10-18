# Lisp Validator

A validation skill for Lisp code across multiple dialects (Clojure, Racket, Scheme, Common Lisp), optimized for LLM workflows.

## Overview

This skill validates Lisp code using dialect-specific tools, providing structured JSON output with precise file:line:col information.

**Supported Dialects:**
- Clojure (clj-kondo + joker)
- Racket/Scheme (raco tools)
- Common Lisp (SBLint + SBCL)
- Emacs Lisp (tree-sitter)

## Installation

### For Claude Code

```sh
# Install to ~/.claude/skills/
./install.sh

# Or package first, then install
./package.sh
unzip lisp-validator.zip -d ~/.claude/skills/lisp-validator/
```

### For Claude.ai

1. Run `./package.sh` to create `lisp-validator.zip`
2. Go to Claude.ai Settings → Skills
3. Upload the zip file

### For Claude API

See [Skills API Documentation](https://docs.claude.com/en/api/skills-guide) for uploading custom skills.

## Quick Start

### Check Available Tools

```sh
python3 scripts/check_tools.py
```

### Validate Code (Auto-Detect Dialect)

```sh
# Auto-detect dialect
python3 scripts/validate.py src/

# Specific file
python3 scripts/validate.py src/core.clj

# Incomplete code (uses tree-sitter)
python3 scripts/validate.py partial.clj --tree-sitter

# Human-readable output
python3 scripts/validate.py src/ --format text
```

## Features

- **Auto-Detection** - Identifies dialect from file extension and content
- **Incomplete Code** - Validates partial expressions via tree-sitter
- **Structured Output** - JSON format for machine parsing
- **Multi-Tool** - Combines complementary validators
- **Progressive Validation** - Fast → Comprehensive workflow
- **Tool Guidance** - Installation detection and recommendations

## Dialect-Specific Usage

### Clojure

```sh
python3 scripts/validate_clojure.py src/
python3 scripts/validate_clojure.py src/ --no-joker  # Skip joker
```

### Racket/Scheme

```sh
python3 scripts/validate_scheme.py src/
python3 scripts/validate_scheme.py file.scm --dialect guile  # Fallback
```

### Common Lisp

```sh
python3 scripts/validate_common_lisp.py src/
python3 scripts/validate_common_lisp.py src/ --no-sbcl  # Skip SBCL
```

## Installation Requirements

**Clojure:**
```sh
brew install borkdude/brew/clj-kondo
brew install candid82/joker/joker
```

**Racket/Scheme:**
```sh
brew install racket
raco pkg install review syntax-warn
```

**Common Lisp:**
```bsh
brew install roswell
ros install sbcl && ros use sbcl
ros install cxxxr/sblint
```

**Universal (all dialects):**
```sh
npm install -g tree-sitter-cli@0.19.3
pip install tree-sitter tree-sitter-commonlisp tree-sitter-clojure tree-sitter-elisp
```

## Example Output

```json
{
  "target": "src/core.clj",
  "dialect": "clojure",
  "findings": [
    {
      "file": "src/core.clj",
      "line": 10,
      "col": 15,
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

## Exit Codes

- **0** - Validation passed
- **2** - Warnings only
- **3** - Errors present

## License

Copyright (C) 2025 Tom Waddington

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

See the [LICENSE](LICENSE) file for the complete license text.
