# ฅ^•ﻌ•^ฅ KittyCode-Agent v2.3

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-Production_Ready-brightgreen.svg)

**The Autonomous AI Coding Agent that lives in your terminal and works in your codebase.**

KittyCode is a production-grade agentic CLI that understands your entire project, plans its own tasks, and writes high-quality code across multiple files autonomously. Designed to be a transparent pair-programmer, you watch her think, plan, and execute in real-time.

>  **Curious how it works under the hood?**  
> Check out the [Architectural Deep Dive & Developer Guide](ABOUT.md) for detailed diagrams, security documentation, and system architecture.

---

## Core Features

*   **Plan-First Autonomous Architecture**: Kitty generates a formal architectural plan and step-by-step queue *before* she starts modifying your files.
*   **Multi-Model Intelligence**: Dynamically routes tasks between state-of-the-art models like Qwen 2.5 Coder, DeepSeek-R1, and GPT-4o based on your preferences. Includes Auto-Healing for API failures.
*   **Live Work Logs**: Real-time terminal feedback for all tool executions (mkdir, write, read, etc.) with intuitive iconography. No black-box operations.
*   **Security Patch 1.0**: Built-in `SandboxValidator` prevents path traversal, encrypts memories locally, and audits for leaked API keys.
*   **Glassmorphic UI**: A premium, high-contrast terminal experience designed for the modern developer.

---

## Quick Start (Installation)

KittyCode works on **Windows, macOS, and Linux**.

### Option A: Global pip installation (Recommended)
```bash
pip install kittycode-agent==2.3.0
```

### Option B: Clone the repository
```bash
git clone https://github.com/Quantum-Blade1/kitty-CLI.git
cd kitty-CLI
# Windows: Double-click install.bat
# Mac/Linux: bash install.sh
```

### Initialize Kitty
After installation, run the setup wizard to connect your AI brains:
```bash
kitty setup
```
*(The wizard will help diagnose PATH issues and guide you through API key setup).*

---

## Usage Commands

| Command | Description |
| :--- | :--- |
| `kitty` | Launch the main REPL (Chat & Code modes) |
| `kitty setup` | Run the onboarding wizard to update keys or themes |
| `kitty secure`| Run Security Patch 1.0 to audit your environment for leaked keys |
| `kitty stats` | View model usage and health telemetry |

---

## Contributing

We welcome contributors! Please review our [Developer Guide](ABOUT.md#5-developer--contributor-guide) to understand the project structure and setup instructions.

## 📄 License
MIT License. Created with by Krish and the KittyCode open-source community.
