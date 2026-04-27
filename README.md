# ฅ^•ﻌ•^ฅ kittycode-agent v2.0

**The Autonomous AI Coding Agent that works in your codebase.**

KittyCode is a production-grade agentic CLI that understands your entire project, plans its own tasks, and writes high-quality code across multiple files autonomously.

---

## Quick Start (Installation)

KittyCode works on **Windows, macOS, and Linux**.

### 1. global pip installation 
pip install kittycode-agent==2.0.0

### 2. Clone the repository
```bash
git clone https://github.com/Quantum-Blade1/kitty-CLI.git
cd kitty-CLI
```

### 3. Run the Installer
*   **Windows**: Double-click `install.bat`
*   **Mac/Linux**: Run `bash install.sh`

### 4. Initialize Kitty
After installation, activate your environment and run the setup wizard:
```bash
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

kitty setup
```

---

## Core Features

*   **Autonomous Coding**: Moves through phases (Plan -> Code -> Verify -> Commit) without needing constant guidance.
*   **Multi-Model Intelligence**: Dynamically routes tasks between Qwen 2.5 Coder, DeepSeek-R1, and GPT-4o for maximum logic and speed.
*   **Live Work Logs**: Watch Kitty work in real-time as she navigates your directories and modifies files.
*   **Glassmorphic UI**: A premium, high-contrast terminal experience designed for the modern developer.

---

## Commands

| Command | Description |
| :--- | :--- |
| `kitty` | Launch the main REPL (Chat & Code modes) |
| `kitty setup` | Re-run the onboarding wizard |
| `kitty stats` | View model usage and health telemetry |
| `kitty about` | Learn about the project philosophy |

---

## License
MIT License. Created with ❤️ by Krish and the KittyCode open-source community.
