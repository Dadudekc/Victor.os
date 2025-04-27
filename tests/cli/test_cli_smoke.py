# tests/cli/test_cli_smoke.py
import subprocess
import sys
import pytest

# Removed xfail marker to enforce smoke tests

@pytest.mark.cli_smoke
@pytest.mark.parametrize("cmd, expected_code, expected_output", [
    ([], 0, ""),  # no args: help
    (["run"], 0, ""),  # run with no args should also show help (exit 0)
    (["run", "--task", "Hello"], 0, ""),  # valid run
])
def test_cli_smoke(cmd, expected_code, expected_output):
    """Run CLI commands and verify exit code and output."""
    process = subprocess.run(
        [sys.executable, "cli.py"] + cmd,
        capture_output=True,
        text=True,
    )
    assert process.returncode == expected_code, \
        f"Expected exit code {expected_code}, got {process.returncode} for cmd: {cmd}\nstderr: {process.stderr}"
    if expected_output:
        # Check in stdout or stderr
        output = process.stdout + process.stderr
        assert expected_output in output, \
            f"Expected '{expected_output}' in output of cmd: {cmd}\nActual output: {output}" 
