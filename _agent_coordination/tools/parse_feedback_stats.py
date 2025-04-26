#!/usr/bin/env python3
"""
Tool to parse feedback logs and stats to assist strategists in next action selection.

Usage:
  parse_feedback_stats.py [--stats <stats_file>] [--feedback-dir <dir>]

Outputs a JSON object with the latest stats snapshot and collected feedback analyses.
"""
import argparse
import json
from pathlib import Path

def load_latest_stats(stats_path: Path):
    text = stats_path.read_text(encoding='utf-8').strip()
    try:
        # Try full JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback to parse last JSON object per line
        last = None
        for line in text.splitlines():
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
        return last

def load_feedback(feedback_dir: Path):
    feedback = []
    if feedback_dir.exists():
        for f in feedback_dir.glob('*.json'):
            try:
                feedback.append(json.loads(f.read_text(encoding='utf-8')))
            except Exception:
                continue
    return feedback

def main():
    parser = argparse.ArgumentParser(description="Parse feedback logs and stats for strategist.")
    parser.add_argument('--stats', default='dream_logs/stats/task_stats.json', help='Path to stats JSON (append mode).')
    parser.add_argument('--feedback-dir', default='dream_logs/feedback', help='Directory containing feedback analysis JSON files.')
    args = parser.parse_args()

    stats_path = Path(args.stats)
    feedback_dir = Path(args.feedback_dir)

    if not stats_path.exists():
        print(json.dumps({'error': f'Stats file not found: {stats_path}'}))
        return

    latest_stats = load_latest_stats(stats_path)
    feedback_items = load_feedback(feedback_dir)

    output = {
        'latest_stats': latest_stats,
        'feedback': feedback_items
    }
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main() 
