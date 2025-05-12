#!/bin/bash
set -euo pipefail

# Dream.OS Onboarding Migration Runner
# Runs validation and migration in sequence with safety checks

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${GREEN}[STATUS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docs/onboarding/migration_spec.yaml" ]; then
    print_error "Must be run from the repository root"
    exit 1
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_status "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Install requirements
print_status "Installing requirements..."
pip install -r docs/onboarding/requirements.txt

# Run validation
print_status "Running migration validation..."
python docs/onboarding/validate_migration.py

if [ $? -ne 0 ]; then
    print_error "Validation failed! Please check migration_validation_report.txt"
    exit 1
fi

# Ask for confirmation before proceeding
read -p "Validation passed. Proceed with migration? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Migration cancelled by user"
    exit 0
fi

# Run dry run first
print_status "Performing dry run..."
python docs/onboarding/migrate.py --dry-run

# Ask for confirmation before actual migration
read -p "Dry run completed. Proceed with actual migration? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Migration cancelled by user"
    exit 0
fi

# Run actual migration
print_status "Executing migration..."
python docs/onboarding/migrate.py

if [ $? -ne 0 ]; then
    print_error "Migration failed! Check migration_execution.log for details"
    exit 1
fi

print_status "Migration completed successfully!"
print_status "Please review the changes and commit them when ready."

# Deactivate virtual environment
deactivate 