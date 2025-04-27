from setuptools import setup, find_packages

setup(
    name="dreamos",
    version="0.1.0",
    description="Dream.OS: Autonomous Auto-Fix Loop and agentic system",
    author="Victor",
    author_email="",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'fastapi',
        'uvicorn',
        'requests',
        'pytest',
        'pyautogui',
        'pyperclip'
    ],
<<<<<<< HEAD
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'dreamos-cli=dreamos.cli.cli:app',
            'dreamos-main=dreamos.cli.main:main',
        ],
    },
) 
=======
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'dreamos-autofix=src.dreamos.agents.autofix_agent:main'
        ]
    }
) 
>>>>>>> 4838cd7da54339e944a554df164ddeb9250cf526
