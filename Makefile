# Dream.OS Makefile

.PHONY: env-check env-report env-clean prebuild pre-publish

# Environment Management
env-check:
	@echo "🔍 Checking Dream.OS environment..."
	@python tools/env/check_env.py

env-report:
	@echo "📊 Generating environment health report..."
	@python tools/env/check_env.py --report-md > docs/system/ENVIRONMENT_STATUS.md
	@echo "✅ Report updated: docs/system/ENVIRONMENT_STATUS.md"

env-clean:
	@echo "🧹 Cleaning environment..."
	@find . -type d -name "__pycache__" -exec rm -r {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Environment cleaned"

# CI/CD Hooks
prebuild: env-check
	@echo "✅ Environment validated for build"

pre-publish: env-check
	@echo "✅ Environment validated for publish"

# Development
install:
	@echo "📦 Installing dependencies..."
	@pip install -r requirements.dev.txt

test:
	@echo "🧪 Running tests..."
	@pytest

lint:
	@echo "🔍 Running linters..."
	@flake8 src tests
	@mypy src
	@black --check src tests
	@isort --check-only src tests

format:
	@echo "🎨 Formatting code..."
	@black src tests
	@isort src tests

# Help
help:
	@echo "Dream.OS Development Commands:"
	@echo "  make env-check    - Check environment health"
	@echo "  make env-report   - Generate environment health report"
	@echo "  make env-clean    - Clean Python cache files"
	@echo "  make prebuild     - Validate environment before build"
	@echo "  make pre-publish  - Validate environment before publish"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make help         - Show this help message" 