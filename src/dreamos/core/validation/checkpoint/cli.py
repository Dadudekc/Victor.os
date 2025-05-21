#!/usr/bin/env python3
"""
Dream.OS Checkpoint Verification CLI

Command-line interface for the Dream.OS Checkpoint Verification Tool.
"""

import os
import sys
import argparse
import logging
from typing import Optional

from dreamos.core.validation.checkpoint import CheckpointVerifier

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("checkpoint_verification_cli")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Checkpoint Verification Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a specific agent's checkpoint implementation")
    verify_parser.add_argument("--agent-id", type=str, required=True, help="ID of the agent to verify")
    verify_parser.add_argument("--checkpoint-dir", type=str, help="Custom checkpoint directory path")
    verify_parser.add_argument("--report-dir", type=str, help="Custom report directory path")
    
    # Verify-all command
    verify_all_parser = subparsers.add_parser("verify-all", help="Verify all agents' checkpoint implementations")
    verify_all_parser.add_argument("--checkpoint-dir", type=str, help="Custom checkpoint directory path")
    verify_all_parser.add_argument("--report-dir", type=str, help="Custom report directory path")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate a verification report")
    report_parser.add_argument("--checkpoint-dir", type=str, help="Custom checkpoint directory path")
    report_parser.add_argument("--output-dir", type=str, help="Output directory for report")
    
    return parser.parse_args()


def main():
    """Main entry point for the verification tool CLI."""
    args = parse_args()
    
    # Create verifier with appropriate directories
    verifier = CheckpointVerifier(
        checkpoint_dir=args.checkpoint_dir if hasattr(args, 'checkpoint_dir') and args.checkpoint_dir else None,
        report_dir=args.report_dir if hasattr(args, 'report_dir') and args.report_dir else None
    )
    
    if args.command == "verify":
        result = verifier.verify_agent(args.agent_id)
        print(f"\nVerification result for {args.agent_id}: {result['overall_result']}")
        
        for test_name, test_result in result["results"].items():
            print(f"  {test_name}: {'SUCCESS' if test_result.get('success', False) else 'FAILED'}")
        
        report_path = verifier.generate_verification_report({args.agent_id: result})
        print(f"Generated verification report at {report_path}")
        
        # Return success/failure status for scripting
        return 0 if result['overall_result'] == "SUCCESS" else 1
    
    elif args.command == "verify-all":
        results = verifier.verify_all_agents()
        
        success_count = 0
        for agent_id, result in results.items():
            print(f"Verification result for {agent_id}: {result['overall_result']}")
            if result['overall_result'] == "SUCCESS":
                success_count += 1
        
        report_path = verifier.generate_verification_report(results)
        print(f"Generated verification report at {report_path}")
        
        # Return success only if all agents succeeded
        return 0 if success_count == len(results) else 1
    
    elif args.command == "report":
        results = verifier.verify_all_agents()
        output_dir = args.output_dir if hasattr(args, 'output_dir') and args.output_dir else None
        report_path = verifier.generate_verification_report(results, output_dir)
        print(f"Generated verification report at {report_path}")
        return 0
    
    else:
        print("No command specified. Use --help for usage information.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 