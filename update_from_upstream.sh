#!/bin/bash

# Script to update forge-llm from upstream Forge repository
# This script fetches the latest changes from the official Forge repository
# and merges them with our LLM integration features

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Forge LLM Update Script"
echo "======================="
echo "This script will update the forge-llm repository with the latest upstream changes"
echo "from the official Forge repository while preserving LLM integration features."
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check if upstream remote exists
if ! git remote get-url upstream &>/dev/null; then
    echo "Adding upstream remote..."
    git remote add upstream https://github.com/Card-Forge/forge.git
fi

# Get current branch
current_branch=$(git symbolic-ref --short HEAD)
echo "Current branch: $current_branch"

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is not clean. Please commit or stash changes."
    git status
    exit 1
fi

# Fetch latest changes from upstream
echo "Fetching latest changes from upstream..."
git fetch upstream

# Get the latest upstream tag
latest_tag=$(git tag -l | grep "forge-" | sort -V | tail -1)
upstream_master_hash=$(git rev-parse upstream/master)
current_hash=$(git rev-parse HEAD)

echo "Latest upstream tag: $latest_tag"
echo "Current commit: $current_hash"
echo "Upstream master: $upstream_master_hash"

# Check if we need to update
if [ "$current_hash" = "$upstream_master_hash" ]; then
    echo "Already up to date with upstream master"
    exit 0
fi

# Create a backup branch
backup_branch="backup-$(date +%Y%m%d-%H%M%S)"
echo "Creating backup branch: $backup_branch"
git branch "$backup_branch"

# Strategy: Rebase our LLM commit on top of the latest upstream master
echo "Rebasing LLM features on top of latest upstream master..."

# Find the LLM commit hash
llm_commit=$(git log --oneline --grep="LLM integration" --format="%H" | head -1)
if [ -z "$llm_commit" ]; then
    echo "Warning: Could not find LLM integration commit, looking for the latest commit..."
    llm_commit=$(git log --oneline -1 --format="%H")
fi

echo "LLM commit: $llm_commit"

# Reset to upstream master
git reset --hard upstream/master

# Cherry-pick the LLM commit
echo "Cherry-picking LLM integration commit..."
if git cherry-pick "$llm_commit"; then
    echo "✅ Successfully merged upstream changes with LLM features"
    echo ""
    echo "Summary of changes:"
    echo "- Updated to latest upstream Forge version"
    echo "- Preserved LLM integration features"
    echo "- Backup created in branch: $backup_branch"
    echo ""
    echo "Next steps:"
    echo "1. Test the updated code"
    echo "2. Build and test the LLM integration"
    echo "3. Push changes to origin: git push origin $current_branch"
    echo "4. If everything works, you can delete the backup: git branch -D $backup_branch"
else
    echo "❌ Cherry-pick failed - there are merge conflicts"
    echo "Please resolve conflicts and run: git cherry-pick --continue"
    echo "Or abort with: git cherry-pick --abort && git reset --hard $backup_branch"
    exit 1
fi

# Show current status
echo ""
echo "Current repository status:"
git log --oneline -5