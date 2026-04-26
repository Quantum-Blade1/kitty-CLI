from setuptools import setup, find_packages

setup(
    name="kittycode-agent",
    version="2.0.0",

    author="Quantum-Blade1",
    description="The autonomous feline coding agent.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",

    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
        "openai>=1.0.0",
        "google-genai>=0.1.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "anthropic>=0.5.0",
        "tiktoken>=0.5.0",
    ],
    entry_points={
        "console_scripts": [
            "kitty=kittycode.cli.app:app",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
