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
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'dreamos-autofix=src.dreamos.agents.autofix_agent:main'
        ]
    }
) 
