# filename: .cursor/queued/consolidate_markdown_and_utilities.prompt.md
Task: Consolidate duplicated Markdown prompts and Python utilities
Context:
  markdown:
    duplicated_files:
      - agent_008/start_prompt.md
      - agent_002/start_prompt.md
      - agent_001/start_prompt.md
      - agent_onboarding_prompt.md
      - competition_protocol.txt
      - task_list resume.txt
  python:
    duplicated_files:
      - _agent_coordination/tools/project_scanner_v1.py
      - _agent_coordination/supervisor_tools/project_scanner/project_scanner.py
      - _agent_coordination/tools/proposal_security_scanner.py (overlaps with scanner)
    tests:
      - tests/test_mailbox_utils.py
Instructions:
  - [Markdown] Extract common content from onboarding prompts into _agent_coordination/onboarding/_start_prompt_template.md.
  - [Markdown] Merge competition_protocol.txt and task_list resume.txt into a unified protocol.md file.
  - [Python] Merge project_scanner_v1.py and project_scanner.py into a single canonical project_scanner.py (preferred location: tools/).
  - [Python Tests] Refactor tests/test_mailbox_utils.py to use parameterized tests instead of repeating assertion blocks.
  - Validate scanner consolidation with a quick dry-run.
  - Commit message suggestion: "refactor: consolidate onboarding prompts, project scanner, and mailbox tests" 