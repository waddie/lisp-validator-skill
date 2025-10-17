#!/bin/bash
#
# Uninstall the lisp-validator skill from Claude Code
#
# This script removes the skill from the default Claude Code skills directory.

set -e

SKILL_NAME="lisp-validator"
SKILLS_DIR="${HOME}/.claude/skills"
INSTALL_DIR="${SKILLS_DIR}/${SKILL_NAME}"

echo "🗑️  Uninstalling ${SKILL_NAME} skill from Claude Code..."

# Check if skill is installed
if [ ! -d "$INSTALL_DIR" ]; then
    echo "   Skill not found at: $INSTALL_DIR"
    echo "   Nothing to uninstall."
    exit 0
fi

# Confirm uninstallation
echo "   Found skill at: $INSTALL_DIR"
read -p "   Confirm uninstallation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "   Uninstallation cancelled."
    exit 0
fi

# Remove skill directory
echo "   Removing skill..."
rm -rf "$INSTALL_DIR"

# Verify removal
if [ ! -d "$INSTALL_DIR" ]; then
    echo ""
    echo "✅ Uninstallation complete!"
    echo "   Skill removed from: $INSTALL_DIR"
else
    echo ""
    echo "❌ Uninstallation failed - directory still exists"
    exit 1
fi
