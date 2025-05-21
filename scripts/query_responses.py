#!/usr/bin/env python3
"""
Response History Query Tool

Usage:
    query_responses.py --agent AGENT_ID [--since TIMESTAMP] [--until TIMESTAMP]
    query_responses.py --hash HASH
    query_responses.py --list-agents
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from dreamos.agents.agent_resume import ResponseHistory

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Query agent response history")
    
    # Query options
    parser.add_argument('--agent', help="Filter by agent ID")
    parser.add_argument('--hash', help="Get specific response by hash")
    parser.add_argument('--list-agents', action='store_true', help="List all agents with responses")
    
    # Time range options
    parser.add_argument('--since', help="Filter responses since timestamp (ISO format)")
    parser.add_argument('--until', help="Filter responses until timestamp (ISO format)")
    
    # Content search options
    parser.add_argument('--search', help="Search responses by content")
    parser.add_argument('--keywords', nargs='+', help="Search responses by keywords")
    parser.add_argument('--case-sensitive', action='store_true', help="Perform case-sensitive search")
    parser.add_argument('--regex', action='store_true', help="Treat search query as regex pattern")
    parser.add_argument('--match-all', action='store_true', help="All keywords must match (AND)")
    
    # Compression options
    parser.add_argument('--compress-now', action='store_true', help="Force immediate rotation and compression")
    parser.add_argument('--retention-days', type=int, default=30, help="Number of days to retain compressed archives")
    
    # Output options
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                      help="Output format (default: text)")
    parser.add_argument('--limit', type=int, help="Limit number of results")
    
    return parser.parse_args()

def load_index() -> dict:
    """Load the response index."""
    index_file = Path("runtime/agent_responses/index.json")
    if not index_file.exists():
        print("No response history found", file=sys.stderr)
        sys.exit(1)
    with open(index_file, 'r') as f:
        return json.load(f)

def get_responses(agent_id: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None) -> list:
    """Get responses matching the filters."""
    index = load_index()
    history_file = Path("runtime/agent_responses/history.jsonl")
    
    # Get relevant hashes
    hashes = set()
    if agent_id:
        hashes.update(index["agents"].get(agent_id, []))
    if since or until:
        for ts, ts_hashes in index["timestamps"].items():
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            hashes.update(ts_hashes)
            
    # If no filters, get all hashes
    if not hashes:
        hashes = set(index["hashes"].keys())
        
    # Read responses
    responses = []
    with open(history_file, 'r') as f:
        for line in f:
            record = json.loads(line)
            if record["hash"] in hashes:
                responses.append(record)
                
    return sorted(responses, key=lambda x: x["timestamp"])

def get_response_by_hash(response_hash: str) -> Optional[dict]:
    """Get a specific response by hash."""
    history_file = Path("runtime/agent_responses/history.jsonl")
    with open(history_file, 'r') as f:
        for line in f:
            record = json.loads(line)
            if record["hash"] == response_hash:
                return record
    return None

def list_agents() -> list:
    """List all agents with responses."""
    index = load_index()
    return sorted(index["agents"].keys())

def format_timestamp(ts: str) -> str:
    """Format timestamp for display."""
    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Query agent response history.')
    parser.add_argument('--agent', help='Filter responses by agent ID')
    parser.add_argument('--since', help='Filter responses since timestamp (ISO format)')
    parser.add_argument('--compress-now', action='store_true', help='Force immediate rotation and compression')
    parser.add_argument('--retention-days', type=int, default=30, help='Number of days to retain archives')
    args = parser.parse_args()

    history = ResponseHistory('runtime/history', args.retention_days)

    if args.compress_now:
        history.compressor.rotate_and_compress()
        print("History rotated and compressed.")
        return

    responses = history.get_responses(agent_id=args.agent, since=args.since)
    print(json.dumps(responses, indent=2))

if __name__ == "__main__":
    sys.exit(main()) 