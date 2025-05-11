from setuptools import find_packages, setup

# Minimal setup.py for compatibility if needed.
# Configuration is primarily in pyproject.toml
setup(
    name="dreamos",  # Basic name, can be refined
    version="0.1.0",  # Placeholder version
    packages=find_packages(where="src"),  # Find packages in the 'src' directory
    package_dir={"": "src"},  # Map package root to 'src'
    install_requires=[
        "argparse",
        "pathlib",
    ],
    entry_points={
        "console_scripts": [
            "dreamos=dreamos.cli.__main__:main",
        ],
    },
    python_requires=">=3.8",
    # Add other metadata like author, description, dependencies if needed
)
