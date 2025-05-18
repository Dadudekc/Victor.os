#!/usr/bin/env python
"""
Dream.OS Social Scout CLI - Command Line Interface for Social Media Lead Finding

This utility provides a simple way to use the social scout system from the command line.
It allows you to search for leads, generate tasks, and create episodes.

Usage:
  python scout_cli.py search twitter --keywords "react,hiring,remote" --max 10
  python scout_cli.py generate-tasks twitter --keywords "python,freelance" --assign Agent-3
  python scout_cli.py create-episode twitter --keywords "ai,machine learning" --name "AI Job Opportunities"
"""

import os
import sys
import argparse
import logging
from typing import List
from pathlib import Path

# Set test mode by default
os.environ["DREAMOS_TEST_MODE"] = "true"

# Import our modules
from dreamos.integrations.social.social_scout import SocialScout
from dreamos.integrations.social.lead_episode_generator import LeadEpisodeGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("scout_cli")

def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Set up the command-line argument parser.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Dream.OS Social Scout CLI - Find leads on social media platforms"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for leads")
    search_parser.add_argument("platform", choices=["twitter", "linkedin"],
                              help="Social platform to search")
    search_parser.add_argument("--keywords", "-k", required=True,
                              help="Comma-separated keywords to search for")
    search_parser.add_argument("--max", "-m", type=int, default=5,
                              help="Maximum number of results (default: 5)")
    search_parser.add_argument("--profile", "-p", 
                              help="Browser profile to use (optional)")
    search_parser.add_argument("--test", "-t", action="store_true",
                              help="Run in test mode with mock data")
    
    # Generate tasks command
    tasks_parser = subparsers.add_parser("generate-tasks", 
                                       help="Search and generate tasks")
    tasks_parser.add_argument("platform", choices=["twitter", "linkedin"],
                             help="Social platform to search")
    tasks_parser.add_argument("--keywords", "-k", required=True,
                             help="Comma-separated keywords to search for")
    tasks_parser.add_argument("--max", "-m", type=int, default=5,
                             help="Maximum number of results (default: 5)")
    tasks_parser.add_argument("--assign", "-a",
                             help="Agent to assign tasks to (e.g. Agent-3)")
    tasks_parser.add_argument("--profile", "-p", 
                             help="Browser profile to use (optional)")
    tasks_parser.add_argument("--test", "-t", action="store_true",
                              help="Run in test mode with mock data")
    
    # Create episode command
    episode_parser = subparsers.add_parser("create-episode", 
                                         help="Create an episode from leads")
    episode_parser.add_argument("platform", choices=["twitter", "linkedin"],
                               help="Social platform to search")
    episode_parser.add_argument("--keywords", "-k", required=True,
                               help="Comma-separated keywords to search for")
    episode_parser.add_argument("--name", "-n", required=True,
                               help="Name for the episode")
    episode_parser.add_argument("--max", "-m", type=int, default=10,
                               help="Maximum number of leads (default: 10)")
    episode_parser.add_argument("--captain", "-c", default="Agent-5",
                               help="Captain agent (default: Agent-5)")
    episode_parser.add_argument("--profile", "-p", 
                               help="Browser profile to use (optional)")
    episode_parser.add_argument("--test", "-t", action="store_true",
                              help="Run in test mode with mock data")
    
    return parser

def parse_keywords(keywords_str: str) -> List[str]:
    """
    Parse comma-separated keywords into a list.
    
    Args:
        keywords_str: Comma-separated string of keywords
        
    Returns:
        List of keywords
    """
    return [k.strip() for k in keywords_str.split(",") if k.strip()]

def search_command(args: argparse.Namespace) -> int:
    """
    Execute the search command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    keywords = parse_keywords(args.keywords)
    if not keywords:
        logger.error("No valid keywords provided")
        return 1
    
    logger.info(f"Searching {args.platform} for: {', '.join(keywords)}")
    
    with SocialScout(platform=args.platform, profile=args.profile) as scout:
        leads = scout.find_leads(keywords=keywords, max_results=args.max)
        
    if not leads:
        logger.warning(f"No leads found on {args.platform} for keywords: {keywords}")
        return 0
        
    logger.info(f"Found {len(leads)} leads on {args.platform}")
    
    # Print a summary of results
    print(f"\n===== {len(leads)} Leads Found =====")
    for i, lead in enumerate(leads, 1):
        print(f"\n--- Lead {i} ---")
        print(f"Platform: {lead['platform']}")
        print(f"Query: {lead['query']}")
        print(f"Username: {lead['username']}")
        print(f"Link: {lead['link']}")
        print(f"Content: {lead['match'][:200]}...")
    
    return 0

def generate_tasks_command(args: argparse.Namespace) -> int:
    """
    Execute the generate-tasks command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    keywords = parse_keywords(args.keywords)
    if not keywords:
        logger.error("No valid keywords provided")
        return 1
        
    logger.info(f"Searching {args.platform} for tasks: {', '.join(keywords)}")
    
    generator = LeadEpisodeGenerator()
    task_ids = generator.search_and_generate_tasks(
        platform=args.platform,
        keywords=keywords,
        assign_to=args.assign,
        max_results=args.max
    )
    
    if not task_ids:
        logger.warning(f"No tasks generated from {args.platform} for keywords: {keywords}")
        return 0
        
    logger.info(f"Generated {len(task_ids)} tasks from {args.platform} leads")
    
    # Print the task IDs
    print(f"\n===== {len(task_ids)} Tasks Generated =====")
    for i, task_id in enumerate(task_ids, 1):
        print(f"{i}. {task_id}")
        
    if args.assign:
        print(f"\nAll tasks assigned to {args.assign}")
    
    return 0

def create_episode_command(args: argparse.Namespace) -> int:
    """
    Execute the create-episode command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    keywords = parse_keywords(args.keywords)
    if not keywords:
        logger.error("No valid keywords provided")
        return 1
        
    logger.info(f"Creating episode from {args.platform} for: {', '.join(keywords)}")
    
    generator = LeadEpisodeGenerator()
    episode_path = generator.create_episode_from_leads(
        platform=args.platform,
        keywords=keywords,
        episode_name=args.name,
        captain_agent=args.captain,
        max_leads=args.max
    )
    
    if not episode_path:
        logger.warning(f"No episode created from {args.platform} for keywords: {keywords}")
        return 0
        
    logger.info(f"Created episode at {episode_path}")
    
    print(f"\n===== Episode Created =====")
    print(f"Name: {args.name}")
    print(f"Platform: {args.platform}")
    print(f"Keywords: {', '.join(keywords)}")
    print(f"Captain: {args.captain}")
    print(f"Path: {episode_path}")
    
    return 0

def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code
    """
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if args.command == "search":
        return search_command(args)
    elif args.command == "generate-tasks":
        return generate_tasks_command(args)
    elif args.command == "create-episode":
        return create_episode_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 