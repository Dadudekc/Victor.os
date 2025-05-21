# Agent 3 Onboarding Guide

## Your Branch
You have been assigned the branch: `agent/agent-3`

## Getting Started
1. We are all working from the same computer at `D:\Dream.os`
2. Checkout your branch:
   ```bash
   git checkout agent/agent-3
   ```
3. Make sure you're up to date:
   ```bash
   git pull origin agent/agent-3
   ```

## Important Resources
- Unified Onboarding Guide: `D:\Dream.os\docs\agents\onboarding\UNIFIED_AGENT_ONBOARDING_GUIDE.md`
- Governance Onboarding: `D:\Dream.os\runtime\governance\onboarding`
- Governance Protocols: `D:\Dream.os\runtime\governance\protocols`
- Agent Proposals: `D:\Dream.os\runtime\governance\proposals`
  - Use this for comments, concerns, tips, and suggestions
  - Create new proposal files for significant changes
  - Review existing proposals before making changes

## Communication Protocol
1. **Primary Method**: Agent Mailboxes
   - Your mailbox: `D:\Dream.os\runtime\agent_comms\agent_mailboxes\agent3\`
   - Meeting notes: `D:\Dream.os\runtime\agent_comms\agent_mailboxes\agent_meeting\`
   - Review meeting README: `D:\Dream.os\runtime\agent_comms\agent_mailboxes\agent_meeting\README.md`

2. **Last Resort**: Cellphone Communication
   - Self-prompting via cellphone is encouraged
   - Use only when mailbox communication is not possible
   - Document all cellphone communications in your branch
   - Create a summary in your mailbox after cellphone discussions

## Development Workflow
1. Before committing any changes:
   - Run your code to ensure it works without errors
   - Test any new functionality you've added
   - Make sure all tests pass
   - Check for any linting issues

2. When committing:
   ```bash
   git add .
   git commit -m "feat(agent3): <your change description>"
   git push origin agent/agent-3
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
- Create proposals for significant changes
- Ask for assistance in the team channel

Remember: Quality first! Always test before you commit. 