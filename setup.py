from setuptools import setup, find_packages

setup(
    name="dreamforge",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "discord.py",
        "pytest",
        "pytest-asyncio",
        "jinja2",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'dreamos-cli=dreamos.cli.cli:app',
            'dreamos-main=dreamos.cli.main:main',
        ],
    },
) 