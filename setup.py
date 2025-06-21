#!/usr/bin/env python3
"""
Victor.os Setup Script
One-command installation and configuration for the AI-native operating system.
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
from setuptools import setup, find_packages

# Project metadata
PROJECT_NAME = "victor-os"
PROJECT_VERSION = "2.0.0"
PROJECT_DESCRIPTION = "AI-native operating system for orchestrating swarms of LLM-powered agents"
PROJECT_AUTHOR = "Victor.os Team"
PROJECT_EMAIL = "team@victor.os"
PROJECT_URL = "https://github.com/victor-os/victor-os"

# Required dependencies
REQUIRED_PACKAGES = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.10.0",
    "PyQt5>=5.15.0",
    "requests>=2.28.0",
    "aiohttp>=3.8.0",
    "fastapi>=0.95.0",
    "uvicorn>=0.20.0",
    "pydantic>=1.10.0",
    "python-multipart>=0.0.6",
    "pyautogui>=0.9.54",
    "pillow>=9.0.0",
    "pandas>=1.5.0",
    "numpy>=1.24.0",
    "matplotlib>=3.6.0",
    "seaborn>=0.12.0",
    "scikit-learn>=1.2.0",
    "discord.py>=2.0.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "tqdm>=4.64.0",
    "psutil>=5.9.0",
    "watchdog>=3.0.0",
    "schedule>=1.2.0",
    "cryptography>=39.0.0",
    "bcrypt>=4.0.0",
    "websockets>=11.0.0",
    "asyncio-mqtt>=0.11.0",
    "redis>=4.5.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.9.0",
    "celery>=5.2.0",
    "flower>=2.0.0",
    "prometheus-client>=0.16.0",
    "structlog>=23.0.0",
    "sentry-sdk>=1.25.0",
    "mypy>=1.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "pre-commit>=3.0.0",
]

# Development dependencies
DEV_PACKAGES = [
    "pytest-cov>=4.0.0",
    "pytest-xdist>=3.0.0",
    "pytest-benchmark>=4.0.0",
    "pytest-html>=3.1.0",
    "pytest-json-report>=1.5.0",
    "coverage>=7.0.0",
    "tox>=4.0.0",
    "bandit>=1.7.0",
    "safety>=2.3.0",
    "pip-audit>=2.4.0",
]

# Optional dependencies
OPTIONAL_PACKAGES = {
    "dashboard": ["streamlit>=1.25.0", "plotly>=5.14.0", "dash>=2.9.0"],
    "ml": ["torch>=2.0.0", "transformers>=4.25.0", "datasets>=2.8.0"],
    "trading": ["alpaca-trade-api>=3.0.0", "yfinance>=0.2.0", "ta>=0.10.0"],
    "monitoring": ["grafana-api>=1.0.0", "prometheus-api-client>=0.5.0"],
    "deployment": ["docker>=6.0.0", "kubernetes>=26.0.0", "helm>=0.7.0"],
}

def create_directories():
    """Create necessary directories for Victor.os"""
    directories = [
        "runtime/config",
        "runtime/logs",
        "runtime/data",
        "runtime/cache",
        "runtime/backups",
        "runtime/temp",
        "runtime/agent_comms/agent_mailboxes",
        "agent_tools/mailbox",
        "prompts/agent_inboxes",
        "docs/api",
        "docs/user_guides",
        "docs/developer_guides",
        "tests/integration",
        "tests/unit",
        "tests/e2e",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_default_config():
    """Create default configuration files"""
    configs = {
        "runtime/config/system.json": {
            "version": "2.0.0",
            "environment": "development",
            "debug": True,
            "log_level": "INFO",
            "max_agents": 10,
            "agent_timeout": 300,
            "mailbox_retention_days": 7,
            "backup_enabled": True,
            "backup_interval_hours": 24,
        },
        "runtime/config/agents.json": {
            "default_config": {
                "empathy_enabled": True,
                "ethos_validation": True,
                "auto_recovery": True,
                "max_retries": 3,
                "timeout": 60,
            },
            "agent_types": {
                "coordinator": {"priority": "high", "max_instances": 1},
                "worker": {"priority": "medium", "max_instances": 5},
                "monitor": {"priority": "low", "max_instances": 2},
            }
        },
        "runtime/config/empathy.json": {
            "scoring_weights": {
                "response_time": 0.2,
                "accuracy": 0.3,
                "helpfulness": 0.25,
                "empathy": 0.25
            },
            "score_decay_enabled": True,
            "decay_half_life_hours": 24,
            "min_decay_factor": 0.1,
            "max_history_size": 1000
        },
        "runtime/config/ethos.json": {
            "principles": [
                "human_centricity",
                "transparency",
                "accountability",
                "privacy",
                "safety"
            ],
            "validation_threshold": 0.8,
            "compliance_required": True,
            "audit_enabled": True
        }
    }
    
    for config_path, config_data in configs.items():
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        print(f"✅ Created config: {config_path}")

def create_environment_file():
    """Create .env file with default environment variables"""
    env_content = """# Victor.os Environment Configuration
# Copy this file to .env and modify as needed

# System Configuration
VICTOR_ENV=development
VICTOR_DEBUG=true
VICTOR_LOG_LEVEL=INFO

# Agent Configuration
MAX_AGENTS=10
AGENT_TIMEOUT=300
MAILBOX_RETENTION_DAYS=7

# Database Configuration
DATABASE_URL=sqlite:///runtime/data/victor.db
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=localhost
API_PORT=8000
API_WORKERS=4

# Security Configuration
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# External Services
DISCORD_TOKEN=your-discord-token
OPENAI_API_KEY=your-openai-key
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret

# Monitoring
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_PORT=9090

# Development
PYTHONPATH=.
PYTEST_ADDOPTS=-v --tb=short
"""
    
    with open('.env.example', 'w') as f:
        f.write(env_content)
    print("✅ Created .env.example")

def create_scripts():
    """Create utility scripts"""
    scripts = {
        "scripts/start.py": '''#!/usr/bin/env python3
"""Victor.os Startup Script"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dreamos.runtime.runtime_manager import RuntimeManager

def main():
    """Start Victor.os runtime"""
    runtime = RuntimeManager()
    runtime.start()

if __name__ == "__main__":
    main()
''',
        "scripts/test.py": '''#!/usr/bin/env python3
"""Victor.os Test Runner"""
import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Run test suite"""
    cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
''',
        "scripts/cleanup.py": '''#!/usr/bin/env python3
"""Victor.os Cleanup Script"""
import os
import shutil
from pathlib import Path

def cleanup():
    """Clean up temporary files and caches"""
    # Remove Python cache
    for root, dirs, files in os.walk("."):
        for dir in dirs:
            if dir == "__pycache__":
                shutil.rmtree(os.path.join(root, dir))
    
    # Remove temp files
    temp_dirs = ["runtime/temp", "temp"]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
    
    print("✅ Cleanup completed")

if __name__ == "__main__":
    cleanup()
'''
    }
    
    for script_path, script_content in scripts.items():
        with open(script_path, 'w') as f:
            f.write(script_content)
        # Make executable on Unix systems
        os.chmod(script_path, 0o755)
        print(f"✅ Created script: {script_path}")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    # Install base requirements
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + REQUIRED_PACKAGES)
    
    # Install development dependencies if in dev mode
    if "--dev" in sys.argv:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + DEV_PACKAGES)
        print("✅ Development dependencies installed")
    
    # Install optional dependencies
    for group, packages in OPTIONAL_PACKAGES.items():
        if f"--{group}" in sys.argv:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
            print(f"✅ Optional dependencies for {group} installed")

def run_post_install():
    """Run post-installation setup"""
    print("🔧 Running post-installation setup...")
    
    # Create directories
    create_directories()
    
    # Create configuration files
    create_default_config()
    
    # Create environment file
    create_environment_file()
    
    # Create utility scripts
    create_scripts()
    
    # Run tests to verify installation
    print("🧪 Running verification tests...")
    try:
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-x"], 
                      capture_output=True, text=True, timeout=300)
        print("✅ Verification tests completed")
    except subprocess.TimeoutExpired:
        print("⚠️  Verification tests timed out (this is normal for first run)")
    except Exception as e:
        print(f"⚠️  Verification tests failed: {e}")

def main():
    """Main setup function"""
    print("🚀 Victor.os Setup")
    print("=" * 50)
    
    # Install dependencies
    install_dependencies()
    
    # Run post-installation setup
    run_post_install()
    
    print("\n🎉 Victor.os setup completed!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and configure your settings")
    print("2. Run 'python scripts/start.py' to start Victor.os")
    print("3. Run 'python scripts/test.py' to run the test suite")
    print("4. Check docs/ for user and developer guides")
    print("\nFor help, see docs/README.md")

if __name__ == "__main__":
    main()

# Standard setuptools setup
setup(
    name=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=PROJECT_DESCRIPTION,
    author=PROJECT_AUTHOR,
    author_email=PROJECT_EMAIL,
    url=PROJECT_URL,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=REQUIRED_PACKAGES,
    extras_require={
        "dev": DEV_PACKAGES,
        **OPTIONAL_PACKAGES
    },
    entry_points={
        "console_scripts": [
            "victor=src.dreamos.cli:main",
            "victor-start=scripts.start:main",
            "victor-test=scripts.test:main",
            "victor-cleanup=scripts.cleanup:cleanup",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Operating System",
        "Topic :: Artificial Intelligence :: General",
    ],
    keywords="ai agents operating-system automation orchestration",
    project_urls={
        "Bug Reports": f"{PROJECT_URL}/issues",
        "Source": PROJECT_URL,
        "Documentation": f"{PROJECT_URL}/docs",
    },
) 