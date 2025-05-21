#!/usr/bin/env python3
"""
Dream.OS Verification Runner

This script runs the Dream.OS verification framework to validate system
components and generates reports on the results.
"""

import os
import sys
import time
import argparse
import json
from pathlib import Path

from dreamos.testing.tools.reliability import ToolReliabilityTester
from dreamos.testing.tools.validation import run_basic_validation, generate_validation_report
from dreamos.core.metrics.metrics_logger import MetricsLogger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Dream.OS verification suite")
    parser.add_argument("--base-path", type=str, default=None,
                        help="Base path for testing")
    parser.add_argument("--output-dir", type=str, default="logs/verification",
                        help="Output directory for reports")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--markdown", action="store_true",
                        help="Output results as Markdown")
    parser.add_argument("--html", action="store_true",
                        help="Output results as HTML")
    parser.add_argument("--only", choices=["reliability", "all"],
                        default="all", help="Only run specific verification")
    return parser.parse_args()

def ensure_output_dir(output_dir):
    """Ensure the output directory exists."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return output_dir

def run_verification(args):
    """Run the verification suite."""
    base_path = args.base_path or os.getcwd()
    output_dir = ensure_output_dir(args.output_dir)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results = {}
    
    print(f"Running Dream.OS verification suite...")
    print(f"Base path: {base_path}")
    print(f"Output directory: {output_dir}")
    
    # Always run basic validation
    validation_results = run_basic_validation(base_path)
    results["validation"] = validation_results
    
    # Generate validation report
    validation_report = generate_validation_report(validation_results)
    print("\n" + validation_report)
    
    # Run tool reliability tests if specified
    if args.only in ["reliability", "all"]:
        print("\nRunning tool reliability tests...")
        tester = ToolReliabilityTester()
        reliability_results = tester.run_comprehensive_test(base_path=base_path)
        results["reliability"] = reliability_results
        
        # Generate reliability report
        reliability_report = tester.generate_report()
        print("\n" + reliability_report)
    
    # Save results
    if args.json or not (args.markdown or args.html):
        json_path = os.path.join(output_dir, f"verification_results_{timestamp}.json")
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nSaved JSON results to {json_path}")
    
    # Always save latest status for CI/CD
    status_path = os.path.join(output_dir, "latest_status.json")
    with open(status_path, "w") as f:
        json.dump({"timestamp": time.time(), "success": validation_results["success"]}, f, indent=2)
    
    if args.markdown or not (args.json or args.html):
        markdown_path = os.path.join(output_dir, f"verification_report_{timestamp}.md")
        with open(markdown_path, "w") as f:
            f.write("# Dream.OS Verification Report\n\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Validation Results\n\n")
            f.write(validation_report)
            if args.only in ["reliability", "all"]:
                f.write("\n\n## Reliability Test Results\n\n")
                f.write(reliability_report)
        print(f"\nSaved Markdown report to {markdown_path}")
    
    if args.html:
        try:
            import markdown
            html_path = os.path.join(output_dir, f"verification_report_{timestamp}.html")
            markdown_content = ""
            markdown_content += "# Dream.OS Verification Report\n\n"
            markdown_content += f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            markdown_content += "## Validation Results\n\n"
            markdown_content += validation_report
            if args.only in ["reliability", "all"]:
                markdown_content += "\n\n## Reliability Test Results\n\n"
                markdown_content += reliability_report
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Dream.OS Verification Report</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 900px; margin: 0 auto; color: #333; }}
                    h1, h2, h3, h4 {{ margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }}
                    h1 {{ font-size: 2em; padding-bottom: .3em; border-bottom: 1px solid #eaecef; }}
                    h2 {{ font-size: 1.5em; padding-bottom: .3em; border-bottom: 1px solid #eaecef; }}
                    h3 {{ font-size: 1.25em; }}
                    h4 {{ font-size: 1em; }}
                    p, ul, ol {{ margin-top: 0; margin-bottom: 16px; }}
                    code {{ font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; padding: 0.2em 0.4em; margin: 0; font-size: 85%; background-color: rgba(27, 31, 35, 0.05); border-radius: 3px; }}
                    pre {{ word-wrap: normal; padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; background-color: #f6f8fa; border-radius: 3px; }}
                    pre code {{ padding: 0; margin: 0; word-break: normal; white-space: pre; background: transparent; border: 0; }}
                    table {{ border-spacing: 0; border-collapse: collapse; margin-top: 0; margin-bottom: 16px; }}
                    table th, table td {{ padding: 6px 13px; border: 1px solid #dfe2e5; }}
                    table th {{ font-weight: 600; }}
                    table tr {{ background-color: #fff; border-top: 1px solid #c6cbd1; }}
                    table tr:nth-child(2n) {{ background-color: #f6f8fa; }}
                </style>
            </head>
            <body>
                {markdown.markdown(markdown_content, extensions=['tables'])}
            </body>
            </html>
            """
            
            with open(html_path, "w") as f:
                f.write(html)
            print(f"\nSaved HTML report to {html_path}")
        except ImportError:
            print("\nWarning: Python 'markdown' package not found. HTML report not generated.")
    
    return validation_results["success"]

def main():
    """Main entry point."""
    args = parse_args()
    success = run_verification(args)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 