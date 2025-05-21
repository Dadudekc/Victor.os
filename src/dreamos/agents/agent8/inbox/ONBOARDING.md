# Agent 8 Onboarding Guide

## Your Branch
You have been assigned the branch: `agent/agent-8`

## Getting Started
1. We are all working from the same computer at `D:\Dream.os`
2. Checkout your branch:
   ```bash
   git checkout agent/agent-8
   ```
3. Make sure you're up to date:
   ```bash
   git pull origin agent/agent-8
   ```

## Important Resources
- Unified Onboarding Guide: `D:\Dream.os\docs\agents\onboarding\UNIFIED_AGENT_ONBOARDING_GUIDE.md`
- Governance Onboarding: `D:\Dream.os\runtime\governance\onboarding`
- Governance Protocols: `D:\Dream.os\runtime\governance\protocols`
- Agent Proposals: `D:\Dream.os\runtime\governance\proposals`

## Communication Protocol
1. **Primary Method**: Use agent mailboxes in `src/dreamos/agents/agent*/inbox/`
2. **Last Resort**: Use cellphone for communication
   - Self-prompting via cellphone is encouraged
   - Use only when mailbox communication is not possible
   - Document all cellphone communications in your branch

## Development Workflow
1. Before committing any changes:
   - Run your code to ensure it works without errors
   - Test any new functionality you've added
   - Make sure all tests pass
   - Check for any linting issues

2. When committing:
   ```bash
   git add .
   git commit -m "feat(agent8): <your change description>"
   git push origin agent/agent-8
   ```

## Testing Requirements
- Always run your code before committing
- Ensure no errors in the console
- Verify all functionality works as expected
- If adding new features, include tests

## Branch Management
- Keep your branch up to date with master
- Create feature branches for large changes
- Merge master into your branch regularly
- Resolve any conflicts promptly
- Wait for captain to merge your work into master

## Need Help?
- Check the unified onboarding guide
- Review the governance protocols
- Use agent mailboxes for communication
- Ask for assistance in the team channel

Remember: Quality first! Always test before you commit. 