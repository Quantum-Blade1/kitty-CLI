from setuptools import setup

setup(
    name="kittycode",
    version="0.1.0",
    py_modules=["main", "kitty_agent"],
    install_requires=[
        "typer",
        "rich",
        "google-generativeai",
        "python-dotenv",
        "pydantic",
    ],
    entry_points={
        "console_scripts": [
            "kitty=main:app",
        ],
    },
)
