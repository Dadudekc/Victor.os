from setuptools import find_packages, setup

setup(
    name="basicbot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "alpaca-trade-api",
        "pytest",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "basicbot=basicbot.strategy:main",  # Allows running `basicbot` in the terminal
        ],
    },
    include_package_data=True,
    author="Your Name",
    description="A trading bot for Alpaca API",
    url="https://github.com/yourrepo/basicbot",  # Update with your repo link
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
