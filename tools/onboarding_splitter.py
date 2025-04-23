#!/usr/bin/env python3
"""
CLI tool to split USER_ONBOARDING.md by section and distribute each section as a Markdown file
into each agent's inbox directory under a base path.
"""
import os
import re
import argparse

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
        if title in sections:
            start = m.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)
            section_text = content[start:end].strip() + '\n'
            # Write section to each agent inbox
            for agent in agents:
                inbox_dir = os.path.join(output_base, agent, 'inbox')
                os.makedirs(inbox_dir, exist_ok=True)
                filename = title.replace(' ', '_') + '.md'
                out_path = os.path.join(inbox_dir, filename)
                with open(out_path, 'w') as out_f:
                    out_f.write(section_text)
                print(f"Written section '{title}' to {out_path}")

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