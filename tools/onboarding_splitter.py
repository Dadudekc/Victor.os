#!/usr/bin/env python3
"""
CLI tool to split USER_ONBOARDING.md by section and distribute each section as a Markdown file
into each agent's inbox directory under a base path.
"""
import sys
from pathlib import Path
import re
import argparse

# Setup Python path to import coordination utils
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))

from _agent_coordination.utils.mailbox_utils import dispatch_message_to_agent

def split_onboarding(input_file: str, output_base: str, agents: list, sections: list):
    # Read full onboarding file
    with open(input_file, 'r') as f:
        content = f.read()
    # Find all Markdown headings (any level) and their positions
    pattern = re.compile(r'(?m)^(?P<header>#+)\s*(?P<title>.+)$')
    matches = list(pattern.finditer(content))
    # Iterate through matches and extract section content
    for i, m in enumerate(matches):
        title = m.group('title').strip()
        # If sections list is empty, include all headings; otherwise filter
        if not sections or title in sections:
            start = m.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)
            section_text = content[start:end].strip() + '\n'
            # Write section to each agent inbox
            for agent in agents:
                # EDIT START: dispatch onboarding section message using shared helper
                mailbox_root = Path(output_base)
                payload = {
                    "event_type": "ONBOARDING_SECTION",
                    "section_title": title,
                    "section_content": section_text
                }
                success = dispatch_message_to_agent(mailbox_root, agent, payload)
                if success:
                    print(f"Dispatched section '{title}' to agent '{agent}' inbox")
                else:
                    print(f"Failed to dispatch section '{title}' to agent '{agent}'")
                # EDIT END

def main():
    parser = argparse.ArgumentParser(
        description='Split USER_ONBOARDING.md into sections and distribute to agents' )
    parser.add_argument('--input', required=True, help='Path to USER_ONBOARDING.md')
    parser.add_argument('--output-base', required=True, help='Base directory for agent inboxes')
    parser.add_argument('--agents', nargs='+', required=True, help='List of agent IDs to receive sections')
    parser.add_argument('--sections', nargs='+', required=True, help='List of section titles to split')
    args = parser.parse_args()
    split_onboarding(args.input, args.output_base, args.agents, args.sections)

if __name__ == '__main__':
    main() 
