#!/usr/bin/env python3
"""
create_feature_plan.py - CLI utility to generate feature specification files based on templates.

Usage:
    python create_feature_plan.py --feature "User Onboarding" [--owner "Agent-1"] [--output "specs/features/"]
"""

import argparse
import os
import sys
import yaml
import uuid
from pathlib import Path
from datetime import datetime

def get_workspace_root():
    """Determine the workspace root directory."""
    # Start from the current file and look for workspace root markers
    current_path = Path(__file__).resolve().parent
    
    # Navigate up the directory tree until we find the workspace root
    # This is identified by having src/dreamos as subdirectories
    max_levels = 10  # Safety limit to prevent infinite loop
    for _ in range(max_levels):
        if (current_path / "src" / "dreamos").exists():
            return current_path
        if current_path.parent == current_path:  # We've reached the filesystem root
            break
        current_path = current_path.parent
    
    # If we can't find the workspace root, use the current working directory
    return Path.cwd()

def load_template(workspace_root):
    """Load the phase 2 feature specification template."""
    template_path = workspace_root / "runtime" / "bootstrapper" / "templates" / "phase_2_feature_spec_template.yaml"
    
    if not template_path.exists():
        print(f"Error: Template file not found at {template_path}")
        sys.exit(1)
    
    with open(template_path, 'r') as f:
        return yaml.safe_load(f)

def create_feature_plan(feature_name, owner=None, output_dir=None):
    """Create a new feature specification from the template."""
    workspace_root = get_workspace_root()
    template = load_template(workspace_root)
    
    # Set the feature name in the template
    if isinstance(template, dict) and 'feature' in template:
        template['feature']['name'] = feature_name
    else:
        print("Error: Template has unexpected structure")
        sys.exit(1)
    
    # Set the owner if provided
    if owner and 'feature' in template:
        # This assumes your template has some way to specify ownership
        # You might need to adjust this based on your actual template structure
        template['feature']['created_by'] = owner
    
    # Create a normalized filename from the feature name
    feature_filename = feature_name.lower().replace(' ', '_').replace('-', '_')
    feature_filename = f"{feature_filename}_spec.yaml"
    
    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = workspace_root / "specs" / "features"
    
    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Full path to the output file
    output_file = output_path / feature_filename
    
    # Write the feature specification to the output file
    with open(output_file, 'w') as f:
        yaml.dump(template, f, sort_keys=False)
    
    print(f"Feature specification created at: {output_file}")
    print("Next steps:")
    print(f"1. Edit {output_file} to fill in the template")
    print("2. Review the specification using the planning prompt")
    print("3. Share with the team for implementation")
    
    return str(output_file)

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='Create a new feature specification from template.')
    parser.add_argument('--feature', required=True, help='Name of the feature to create')
    parser.add_argument('--owner', help='Owner of the feature (e.g., Agent-1)')
    parser.add_argument('--output', help='Output directory for the specification file')
    
    args = parser.parse_args()
    
    create_feature_plan(args.feature, args.owner, args.output)

if __name__ == "__main__":
    main() 