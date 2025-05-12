"""
Setup script for Dream.OS
"""

from setuptools import setup, find_packages

setup(
    name="dreamos",
    version="0.1.0",
    description="Dream.OS - An autonomous agent framework",
    author="Dream.OS Team",
    author_email="team@dream.os",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "typing-extensions>=4.5.0",
        "loguru>=0.7.0",
        "pyyaml>=6.0.0",
        "jsonschema>=4.17.0",
        "python-dateutil>=2.8.2",
        "colorama>=0.4.6",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "pylint>=2.17.0",
            "pytest-cov>=4.0.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 