"""
Web Dashboard for Module Validation Framework.

This module provides a web dashboard for visualizing the validation status of
Dream.OS bridge modules, including interface compliance, error handling,
and integration test results.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List

def get_latest_dashboard_data(data_dir: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest dashboard data from the data directory.
    
    Args:
        data_dir: Directory containing dashboard data
        
    Returns:
        Optional[Dict[str, Any]]: Latest dashboard data or None if no data found
    """
    latest_path = os.path.join(data_dir, "latest.json")
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading latest dashboard data: {str(e)}")
            return None
    
    # Look for the most recent data file
    data_files = [
        f for f in os.listdir(data_dir)
        if f.startswith("dashboard_data_") and f.endswith(".json")
    ]
    
    if not data_files:
        return None
    
    # Sort by timestamp (assuming filename is dashboard_data_{timestamp}.json)
    data_files.sort(reverse=True)
    latest_file = data_files[0]
    
    try:
        with open(os.path.join(data_dir, latest_file), "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading dashboard data: {str(e)}")
        return None

def generate_web_dashboard(data: Dict[str, Any]) -> str:
    """
    Generate a web dashboard from dashboard data.
    
    Args:
        data: Dashboard data
        
    Returns:
        str: HTML dashboard
    """
    modules = data.get("modules", {})
    errors = data.get("errors", [])
    timestamp = data.get("timestamp", time.time())
    
    # Generate HTML
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("  <meta charset='UTF-8'>")
    html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append("  <title>Module Validation Dashboard</title>")
    html.append("  <style>")
    html.append("    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }")
    html.append("    h1, h2, h3 { color: #333; }")
    html.append("    .dashboard { max-width: 1200px; margin: 0 auto; }")
    html.append("    .header { background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }")
    html.append("    .overall { font-size: 1.2em; margin-top: 10px; }")
    html.append("    .module-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }")
    html.append("    .module-table th, .module-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
    html.append("    .module-table th { background-color: #f2f2f2; }")
    html.append("    .module-table tr:nth-child(even) { background-color: #f9f9f9; }")
    html.append("    .status-Pass { color: green; }")
    html.append("    .status-Fail { color: red; }")
    html.append("    .status-Partial { color: orange; }")
    html.append("    .status-Unknown { color: gray; }")
    html.append("    .error-list { background-color: #fff0f0; padding: 10px; border-radius: 5px; margin-bottom: 20px; }")
    html.append("    .error-list h3 { color: #d32f2f; }")
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")
    html.append("  <div class='dashboard'>")
    html.append("    <div class='header'>")
    html.append("      <h1>Module Validation Dashboard</h1>")
    html.append(f"      <div>Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}</div>")
    
    # Overall status
    overall_status = "Pass"
    for module in modules.values():
        if module["overall"] == "Fail":
            overall_status = "Fail"
            break
        elif module["overall"] == "Partial" and overall_status != "Fail":
            overall_status = "Partial"
    
    html.append(f"      <div class='overall'>Overall Status: <span class='status-{overall_status}'>{overall_status}</span></div>")
    html.append("    </div>")
    
    # Modules table
    html.append("    <h2>Module Status</h2>")
    html.append("    <table class='module-table'>")
    html.append("      <tr>")
    html.append("        <th>Module</th>")
    html.append("        <th>Interface Compliance</th>")
    html.append("        <th>Error Handling</th>")
    html.append("        <th>Integration Tests</th>")
    html.append("        <th>Overall</th>")
    html.append("      </tr>")
    
    for module_name, module in sorted(modules.items()):
        html.append("      <tr>")
        html.append(f"        <td>{module_name}</td>")
        html.append(f"        <td class='status-{module['interface_compliance']}'>{module['interface_compliance']}</td>")
        html.append(f"        <td class='status-{module['error_handling']}'>{module['error_handling']}</td>")
        html.append(f"        <td class='status-{module['integration_tests']}'>{module['integration_tests']}</td>")
        html.append(f"        <td class='status-{module['overall']}'>{module['overall']}</td>")
        html.append("      </tr>")
    
    html.append("    </table>")
    
    # Errors
    if errors:
        html.append("    <div class='error-list'>")
        html.append("      <h3>Errors</h3>")
        html.append("      <ul>")
        for error in errors:
            html.append(f"        <li>{error}</li>")
        html.append("      </ul>")
        html.append("    </div>")
    
    html.append("  </div>")
    html.append("</body>")
    html.append("</html>")
    
    return "\n".join(html)

def save_web_dashboard(html: str, output_path: str) -> bool:
    """
    Save a web dashboard to a file.
    
    Args:
        html: HTML dashboard to save
        output_path: Path to save the HTML file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w") as f:
            f.write(html)
        
        return True
    except Exception as e:
        print(f"Error saving web dashboard: {str(e)}")
        return False

def generate_and_save_dashboard(data_dir: str, output_path: str) -> bool:
    """
    Generate and save a web dashboard from the latest data.
    
    Args:
        data_dir: Directory containing dashboard data
        output_path: Path to save the HTML file
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get the latest data
    data = get_latest_dashboard_data(data_dir)
    if not data:
        print("No dashboard data found")
        return False
    
    # Generate the dashboard
    html = generate_web_dashboard(data)
    
    # Save the dashboard
    return save_web_dashboard(html, output_path)

def main() -> int:
    """
    Main entry point when run as a script.
    
    Returns:
        int: Exit code
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate a web dashboard from Module Validation Framework results')
    parser.add_argument('--data-dir', type=str, default='logs/module_validation',
                        help='Directory containing dashboard data')
    parser.add_argument('--output', type=str, default='logs/module_validation/dashboard.html',
                        help='Path to save the HTML dashboard')
    
    args = parser.parse_args()
    
    success = generate_and_save_dashboard(args.data_dir, args.output)
    
    if success:
        print(f"Dashboard generated successfully: {args.output}")
        return 0
    else:
        print("Failed to generate dashboard: No data found")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 