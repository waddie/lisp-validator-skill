#!/bin/bash
#
# Package the lisp-validator skill into a distributable zip file
#
# This script creates a clean package containing only the necessary skill files,
# excluding development artifacts, git history, and cache files.

set -e

SKILL_NAME="lisp-validator"
OUTPUT_FILE="${SKILL_NAME}.zip"

echo "📦 Packaging ${SKILL_NAME} skill..."

# Remove old package if it exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "   Removing existing package..."
    rm "$OUTPUT_FILE"
fi

# Create zip file with skill contents
# Excludes: .git, .jj, .claude, __pycache__, and other development files
echo "   Creating archive..."
zip -r "$OUTPUT_FILE" \
    SKILL.md \
    LICENSE \
    README.md \
    CLAUDE.md \
    scripts/ \
    references/ \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "*.swp" \
    -x "*.swo" \
    -x "*~" \
    -x ".DS_Store" \
    -x ".git/*" \
    -x ".jj/*" \
    -x ".claude/*" \
    -x "*.zip" \
    -x ".clj-kondo/*" \
    -x ".cache/*"

# Show package contents
echo "   Package contents:"
unzip -l "$OUTPUT_FILE" | head -20

# Show file size
SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo ""
echo "✅ Package created: $OUTPUT_FILE ($SIZE)"
echo ""
echo "To install this skill:"
echo "  • Claude.ai: Upload via Skills settings"
echo "  • Claude Code: Use './install.sh' or manually copy to ~/.claude/skills/"
echo "  • Claude API: Upload via Skills API endpoint"
