# Victor.os Quick Start Guide

**Get Victor.os running in 5 minutes!**

## 🚀 One-Command Installation

### Prerequisites
- Python 3.10 or higher
- 4GB+ RAM (recommended)
- 1GB+ free disk space

### Installation

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd Victor.os

# Run the one-command installer
python scripts/install.py
```

The installer will:
- ✅ Check system requirements
- ✅ Install all dependencies
- ✅ Create directory structure
- ✅ Generate default configurations
- ✅ Run verification tests

## 🎯 First Steps

### 1. Configure Your Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration (optional for basic usage)
# nano .env
```

### 2. Start Victor.os

```bash
# Start the runtime
python scripts/start.py

# Or use the CLI
python -m src.dreamos.cli runtime --start
```

### 3. Verify Installation

```bash
# Run the test suite
python scripts/test.py

# Or use the CLI
python -m src.dreamos.cli test

# Check system status
python -m src.dreamos.cli status
```

## 🛠️ CLI Commands

Victor.os includes a comprehensive CLI for all operations:

### System Management
```bash
# Check system status
python -m src.dreamos.cli status

# Start/stop runtime
python -m src.dreamos.cli runtime --start
python -m src.dreamos.cli runtime --stop

# Clean up files
python -m src.dreamos.cli cleanup
```

### Testing & Development
```bash
# Run tests
python -m src.dreamos.cli test

# Run with coverage
python -m src.dreamos.cli test --coverage

# Generate documentation
python -m src.dreamos.cli generate --docs

# Diagnose installation
python -m src.dreamos.cli doctor
```

### Agent Management
```bash
# List all agents
python -m src.dreamos.cli agent --list

# Create new agent
python -m src.dreamos.cli agent --create my-agent

# Check agent status
python -m src.dreamos.cli agent --status my-agent
```

### Dashboard
```bash
# Launch the GUI dashboard
python -m src.dreamos.cli dashboard
```

## 📊 Dashboard

Launch the visual dashboard to monitor your agents:

```bash
python -m src.dreamos.cli dashboard
```

The dashboard provides:
- Real-time agent status
- Message queue management
- System metrics
- Log viewing
- Configuration management

## 🔧 Configuration

### System Configuration
Located in `runtime/config/system.json`:
```json
{
  "version": "2.0.0",
  "environment": "development",
  "debug": true,
  "log_level": "INFO",
  "max_agents": 10,
  "agent_timeout": 300
}
```

### Agent Configuration
Located in `runtime/config/agents.json`:
```json
{
  "default_config": {
    "empathy_enabled": true,
    "ethos_validation": true,
    "auto_recovery": true,
    "max_retries": 3
  }
}
```

### Environment Variables
Key variables in `.env`:
```bash
# System
VICTOR_ENV=development
VICTOR_DEBUG=true
VICTOR_LOG_LEVEL=INFO

# Agents
MAX_AGENTS=10
AGENT_TIMEOUT=300

# API
API_HOST=localhost
API_PORT=8000
```

## 🧪 Testing

### Run All Tests
```bash
python -m src.dreamos.cli test
```

### Run Specific Test Types
```bash
# Unit tests only
python -m src.dreamos.cli test --unit

# Integration tests only
python -m src.dreamos.cli test --integration

# With coverage report
python -m src.dreamos.cli test --coverage
```

### Test Results
- **44 tests passing** (core functionality)
- **231 tests** (comprehensive coverage)
- Coverage reports in `htmlcov/`

## 🔍 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Check Python path
python -m src.dreamos.cli doctor

# Reinstall dependencies
python scripts/install.py
```

#### Permission Errors
```bash
# Clean up and retry
python -m src.dreamos.cli cleanup

# Check file permissions
ls -la runtime/
```

#### Dashboard Won't Start
```bash
# Install PyQt5
pip install PyQt5

# Check display settings
python -m src.dreamos.cli doctor
```

### Getting Help

1. **Check the logs**: `runtime/logs/`
2. **Run diagnostics**: `python -m src.dreamos.cli doctor`
3. **Verify installation**: `python scripts/install.py`
4. **Check documentation**: `docs/`

## 📚 Next Steps

### Basic Usage
1. **Create your first agent**:
   ```bash
   python -m src.dreamos.cli agent --create my-first-agent
   ```

2. **Monitor with dashboard**:
   ```bash
   python -m src.dreamos.cli dashboard
   ```

3. **Run a test workflow**:
   ```bash
   python -m src.dreamos.cli test --integration
   ```

### Advanced Usage
- **Custom agent development**: See `docs/developer_guides/`
- **API integration**: See `docs/api/`
- **Configuration tuning**: See `docs/user_guides/CONFIGURATION.md`
- **Deployment**: See `docs/user_guides/DEPLOYMENT.md`

## 🎉 Success!

You now have Victor.os running! The system provides:

- ✅ **Agent Communication Infrastructure** - Production ready
- ✅ **Dashboard & Monitoring** - Functional GUI
- ✅ **Agent Framework** - Core ready
- ✅ **Testing Infrastructure** - Comprehensive test suite
- ✅ **CLI Tools** - Complete command-line interface
- ✅ **Documentation** - Extensive guides and references

## 📞 Support

- **Documentation**: `docs/`
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Roadmap**: `docs/ROADMAP.md`

---

**Welcome to Victor.os!** 🚀

The AI-native operating system for orchestrating swarms of LLM-powered agents. 