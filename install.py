#!/usr/bin/env python3
"""
Victor.os One-Command Installer
Quick setup script for getting Victor.os running in minutes.
"""

import os
import sys
import subprocess
import json
import shutil
import platform
from pathlib import Path

def print_banner():
    """Print Victor.os banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║                    🚀 Victor.os Setup                       ║
    ║                                                              ║
    ║         AI-native operating system for agent swarms         ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def check_system_requirements():
    """Check system requirements"""
    print("\n🔍 Checking system requirements...")
    
    # Check available memory (at least 4GB recommended)
    try:
        import psutil
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb < 4:
            print(f"⚠️  Low memory detected: {memory_gb:.1f}GB (4GB+ recommended)")
        else:
            print(f"✅ Memory: {memory_gb:.1f}GB")
    except ImportError:
        print("⚠️  Could not check memory (psutil not available)")
    
    # Check disk space (at least 1GB free)
    try:
        disk_usage = shutil.disk_usage(".")
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 1:
            print(f"❌ Insufficient disk space: {free_gb:.1f}GB free (1GB+ required)")
            sys.exit(1)
        else:
            print(f"✅ Disk space: {free_gb:.1f}GB free")
    except Exception:
        print("⚠️  Could not check disk space")

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    # Core dependencies
    core_deps = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
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
        "discord.py>=2.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "psutil>=5.9.0",
        "websockets>=11.0.0",
        "redis>=4.5.0",
        "sqlalchemy>=2.0.0",
        "structlog>=23.0.0",
    ]
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + core_deps)
        print("✅ Core dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

def create_directory_structure():
    """Create necessary directories"""
    print("\n📁 Creating directory structure...")
    
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
        print(f"   ✅ {directory}")

def create_default_configs():
    """Create default configuration files"""
    print("\n⚙️  Creating default configurations...")
    
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
        print(f"   ✅ {config_path}")

def create_environment_file():
    """Create .env file"""
    print("\n🌍 Creating environment configuration...")
    
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
SECRET_KEY=your-secret-key-here-change-this-in-production
ENCRYPTION_KEY=your-encryption-key-here-change-this-in-production

# External Services (optional)
DISCORD_TOKEN=your-discord-token
OPENAI_API_KEY=your-openai-key
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_PORT=9090

# Development
PYTHONPATH=.
PYTEST_ADDOPTS=-v --tb=short
"""
    
    with open('.env.example', 'w') as f:
        f.write(env_content)
    print("   ✅ .env.example created")

def create_utility_scripts():
    """Create utility scripts"""
    print("\n🔧 Creating utility scripts...")
    
    scripts = {
        "scripts/start.py": '''#!/usr/bin/env python3
"""Victor.os Startup Script"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Start Victor.os runtime"""
    try:
        from src.dreamos.runtime.runtime_manager import RuntimeManager
        runtime = RuntimeManager()
        runtime.start()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Startup error: {e}")
        sys.exit(1)

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
    print("🧪 Running Victor.os test suite...")
    cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")

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
    print("🧹 Cleaning up temporary files...")
    
    # Remove Python cache
    for root, dirs, files in os.walk("."):
        for dir in dirs:
            if dir == "__pycache__":
                cache_path = os.path.join(root, dir)
                shutil.rmtree(cache_path)
                print(f"   ✅ Removed {cache_path}")
    
    # Remove temp files
    temp_dirs = ["runtime/temp", "temp"]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            print(f"   ✅ Cleaned {temp_dir}")
    
    print("✅ Cleanup completed")

if __name__ == "__main__":
    cleanup()
'''
    }
    
    for script_path, script_content in scripts.items():
        with open(script_path, 'w') as f:
            f.write(script_content)
        # Make executable on Unix systems
        if platform.system() != "Windows":
            os.chmod(script_path, 0o755)
        print(f"   ✅ {script_path}")

def run_verification():
    """Run verification tests"""
    print("\n🧪 Running verification tests...")
    
    try:
        # Quick import test
        sys.path.insert(0, "src")
        import dreamos
        print("   ✅ Core modules import successfully")
        
        # Run a few basic tests
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-x", "-k", "not slow"],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            print("   ✅ Verification tests passed")
        else:
            print("   ⚠️  Some verification tests failed (this is normal for first run)")
            print("   📝 Check the output above for details")
            
    except ImportError as e:
        print(f"   ⚠️  Import verification failed: {e}")
        print("   📝 Some modules may need additional setup")
    except subprocess.TimeoutExpired:
        print("   ⚠️  Verification tests timed out (this is normal for first run)")
    except Exception as e:
        print(f"   ⚠️  Verification failed: {e}")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 Victor.os installation completed!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Configure your environment:")
    print("   cp .env.example .env")
    print("   # Edit .env with your settings")
    
    print("\n2. Start Victor.os:")
    print("   python scripts/start.py")
    
    print("\n3. Run tests:")
    print("   python scripts/test.py")
    
    print("\n4. Clean up when needed:")
    print("   python scripts/cleanup.py")
    
    print("\n📚 Documentation:")
    print("   - User Guide: docs/user_guides/")
    print("   - API Reference: docs/api/")
    print("   - Developer Guide: docs/developer_guides/")
    
    print("\n🔧 Troubleshooting:")
    print("   - Check logs in runtime/logs/")
    print("   - Verify configuration in runtime/config/")
    print("   - Run tests to verify installation")
    
    print("\n💡 Tips:")
    print("   - Start with the basic configuration")
    print("   - Add external services (Discord, OpenAI) gradually")
    print("   - Check the roadmap in docs/ROADMAP.md")
    
    print("\n🚀 Welcome to Victor.os!")

def main():
    """Main installation function"""
    print_banner()
    
    # Check requirements
    check_python_version()
    check_system_requirements()
    
    # Install dependencies
    install_dependencies()
    
    # Setup project structure
    create_directory_structure()
    create_default_configs()
    create_environment_file()
    create_utility_scripts()
    
    # Verify installation
    run_verification()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1) 