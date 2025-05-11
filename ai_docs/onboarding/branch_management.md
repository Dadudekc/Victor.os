# Agent Branch Management Guide

## Overview

This guide outlines the branch management strategy for agents working in the Dream.OS project. Each agent should maintain its own branch for all changes and contributions.

## Branch Naming Convention

- Each agent should create and use a branch named `agent{N}` where N is the agent's ID number
- Example: `agent1`, `agent2`, etc.
- This ensures clear separation of work and prevents conflicts between agents

## Getting Started

1. **Initial Setup**
   ```bash
   # Clone the repository (if not already done)
   git clone <repository-url>
   cd Dream.os
   
   # Create your agent branch
   git checkout -b agent{N}  # Replace N with your agent ID
   ```

2. **Before Starting Work**
   ```bash
   # Always start from an up-to-date main branch
   git checkout main
   git pull origin main
   
   # Create/switch to your agent branch
   git checkout agent{N}
   git merge main  # Ensure your branch is up to date
   ```

## Workflow

1. **Making Changes**
   - All changes should be made on your agent branch
   - Commit frequently with clear, descriptive messages
   - Follow the conventional commit format:
     ```
     feat(area): description
     fix(area): description
     docs(area): description
     ```

2. **Pushing Changes**
   ```bash
   # Push your changes to your agent branch
   git push origin agent{N}
   ```

3. **Keeping Up to Date**
   ```bash
   # Regularly sync with main
   git checkout main
   git pull origin main
   git checkout agent{N}
   git merge main
   ```

## Best Practices

1. **Commit Messages**
   - Use clear, descriptive messages
   - Reference task IDs when applicable
   - Follow conventional commit format

2. **Branch Hygiene**
   - Keep your branch up to date with main
   - Resolve conflicts promptly
   - Don't let your branch drift too far from main

3. **Code Review**
   - All changes should be reviewed before merging to main
   - Use pull requests for code review
   - Address review comments promptly

4. **Conflict Resolution**
   - Resolve conflicts in your agent branch
   - Test thoroughly after resolving conflicts
   - Seek help if conflicts are complex

## Common Commands

```bash
# Check current branch
git branch

# Switch to your agent branch
git checkout agent{N}

# Create and switch to your agent branch
git checkout -b agent{N}

# Update your branch with main
git checkout main
git pull origin main
git checkout agent{N}
git merge main

# Push your changes
git push origin agent{N}

# View commit history
git log --oneline
```

## Troubleshooting

1. **Merge Conflicts**
   ```bash
   # If you encounter merge conflicts
   git status  # Check which files have conflicts
   # Resolve conflicts in the files
   git add <resolved-files>
   git commit -m "Resolve merge conflicts"
   ```

2. **Accidental Commits to Main**
   ```bash
   # If you accidentally committed to main
   git checkout main
   git reset --hard HEAD~1  # Undo last commit
   git checkout agent{N}
   # Make your changes here instead
   ```

3. **Lost Changes**
   ```bash
   # If you need to recover lost changes
   git reflog  # Find the commit hash
   git checkout <commit-hash>
   git checkout -b agent{N}-recovery
   ```

## Security Notes

1. **Never commit sensitive data**
   - API keys
   - Passwords
   - Personal information
   - Environment-specific configurations

2. **Use .gitignore**
   - Keep the `.gitignore` file up to date
   - Add any new sensitive or generated files

## Support

If you encounter any issues with branch management:
1. Check this guide first
2. Review git documentation
3. Contact the project maintainers
4. Use the agent communication channels for help

Remember: Your agent branch is your workspace. Keep it clean, up to date, and well-organized. 