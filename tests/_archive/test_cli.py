import pytest
from typer.testing import CliRunner
from cli import app

runner = CliRunner()

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "dream-os" in result.stdout or "Commands:" in result.stdout


def test_run_missing_config():
    # --config requires an existing file
    result = runner.invoke(app, ["run", "--config", "nonexistent.yaml"])
    assert result.exit_code != 0
    # Typer should report missing file error
    assert "Error" in result.stdout or "Error" in result.stderr 
