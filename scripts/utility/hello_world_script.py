import os
import sys

# Try importing something from the project to test PYTHONPATH
try:
    from dreamos.version import __version__

    print(f"Successfully imported dreamos version: {__version__}")
except ImportError as e:
    print(f"ERROR: Failed to import dreamos: {e}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"sys.path: {sys.path}")
    exit(1)

print("Hello from test script!")
print(f"Arguments received: {sys.argv[1:]}")
print(f"Current working directory: {os.getcwd()}")

# Example of producing stderr output
# print("This is an error message.", file=sys.stderr)

# Example of non-zero exit code
# sys.exit(2)
