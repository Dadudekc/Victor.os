#!/usr/bin/env python3
"""
Broadcast Directive Tool

This script sends a given directive content as a message to all agent mailboxes under _agent_coordination/shared_mailboxes.
"""
import os
import json
import glob
from datetime import datetime, timezone

def broadcast_to_mailboxes(content, directive_id=None):
    # Determine mailbox directory
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared_mailboxes'))
    pattern = os.path.join(base, 'mailbox_*.json')
    # Create a unique directive ID if not provided
    if directive_id is None:
        t = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        directive_id = f'swarm-resume-{t}'

    for path in glob.glob(pattern):
        try:
            with open(path, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                # Prepare message object
                msg = {
                    'id': directive_id,
                    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'content': content
                }
                # Ensure messages list exists
                msgs = data.get('messages')
                if not isinstance(msgs, list):
                    data['messages'] = []
                    msgs = data['messages']
                msgs.append(msg)
                # Write back
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
            print(f'Broadcast sent to {os.path.basename(path)}')
        except Exception as e:
            print(f'Failed to send to {path}: {e}')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Broadcast a directive to all agent mailboxes')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--content', help='Directive text to broadcast')
    group.add_argument('--file', dest='file_path', help='Path to text file containing directive')
    parser.add_argument('--directive-id', dest='directive_id', help='Optional custom directive ID')
    args = parser.parse_args()
    if args.file_path:
        try:
            with open(args.file_path, 'r', encoding='utf-8') as tf:
                content = tf.read()
        except Exception as e:
            print(f'Failed to read file {args.file_path}: {e}')
            exit(1)
    else:
        content = args.content
    broadcast_to_mailboxes(content, args.directive_id) 