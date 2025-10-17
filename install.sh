#!/bin/bash
#
# Install the lisp-validator skill to Claude Code
#
# This script installs the skill to the default Claude Code skills directory.
# For Claude.ai or Claude API, use the web interface or API instead.

set -e

SKILL_NAME="lisp-validator"
SKILLS_DIR="${HOME}/.claude/skills"
INSTALL_DIR="${SKILLS_DIR}/${SKILL_NAME}"

echo "🔧 Installing ${SKILL_NAME} skill to Claude Code..."

# Check if Claude Code skills directory exists
if [ ! -d "$SKILLS_DIR" ]; then
    echo "   Creating skills directory: $SKILLS_DIR"
    mkdir -p "$SKILLS_DIR"
fi

# Check if skill already installed
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Skill already installed at: $INSTALL_DIR"
    read -p "   Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "   Installation cancelled."
        exit 0
    fi
    echo "   Removing existing installation..."
    rm -rf "$INSTALL_DIR"
fi

# Create installation directory
echo "   Creating installation directory..."
mkdir -p "$INSTALL_DIR"

# Copy skill files
echo "   Copying skill files..."
cp SKILL.md "$INSTALL_DIR/"
cp LICENSE "$INSTALL_DIR/"
cp README.md "$INSTALL_DIR/"
cp CLAUDE.md "$INSTALL_DIR/"
cp -r scripts "$INSTALL_DIR/"
cp -r references "$INSTALL_DIR/"

# Make scripts executable
echo "   Setting executable permissions..."
chmod +x "$INSTALL_DIR"/scripts/*.py

# Verify installation
if [ -f "$INSTALL_DIR/SKILL.md" ]; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "Skill installed to: $INSTALL_DIR"
    echo ""
    echo "Usage in Claude Code:"
    echo "  • Skills are automatically loaded from ~/.claude/skills/"
    echo "  • Check available tools: python3 ~/.claude/skills/${SKILL_NAME}/scripts/check_tools.py"
    echo "  • Validate code: python3 ~/.claude/skills/${SKILL_NAME}/scripts/validate.py <file>"
    echo ""
    echo "To uninstall:"
    echo "  rm -rf $INSTALL_DIR"
else
    echo ""
    echo "❌ Installation failed - SKILL.md not found in installation directory"
    exit 1
fi
