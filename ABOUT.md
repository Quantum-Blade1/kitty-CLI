# ฅ^•ﻌ•^ฅ KittyCode: Architectural Deep Dive & Documentation

Welcome to the definitive architectural guide for **KittyCode-Agent**. This document provides a comprehensive look into how Kitty works under the hood, detailing every minute component, data flow, and security measure that powers this autonomous coding assistant.

---

## 1. Philosophy & Vision

KittyCode was designed with a core philosophy: **"An AI assistant should be a transparent pair-programmer, not a black box."** 

Unlike traditional code generators that blindly spit out code, KittyCode operates through an **Autonomous Loop** with built-in reflection, planning, and real-time observability. You see every tool she uses, every file she reads, and every plan she formulates.

---

## 2. System Architecture

The architecture is built around a central `KittyAgent` that acts as the orchestrator. It connects the user interface (CLI) to the intelligence layer (Models), execution layer (Tools), and state management (Memory & Context).

```mermaid
flowchart TD
    User([User CLI]) <--> App[CLI App / UI]
    App <--> Agent[KittyAgent]
    
    subgraph Intelligence Layer
        Agent <--> Planner[Task Planner]
        Agent <--> Router[Model Router]
        Router --> Qwen[Qwen 2.5 Coder]
        Router --> DeepSeek[DeepSeek-R1]
        Router --> GPT4o[GPT-4o]
        Router -.-> Fallback[Quantum Fallback]
    end
    
    subgraph Execution Layer
        Agent <--> ToolEngine[Tool Engine]
        ToolEngine <--> Sandbox[Sandbox Validator]
        Sandbox --> FileSystem[(File System)]
        Sandbox --> Git[Git Integration]
    end
    
    subgraph State Management
        Agent <--> Context[Codebase Indexer]
        Agent <--> Memory[Structured Memory]
        Memory <--> Vault[Security Vault]
    end
```

---

## 3. Core Components Deep Dive

### 3.1 The Autonomous Loop (Agent & Planner)

The brain of the operation lives in `kittycode/agent/kitty.py`. When in "Code Mode", Kitty does not immediately start writing code. Instead, she utilizes a **Plan-First Architecture**.

1. **Task Ingestion**: The user provides a goal.
2. **Context Gathering**: The `Codebase Indexer` (`ls_tree` + `read_file`) pulls relevant project structure and system prompts.
3. **Planning Phase**: The `Planner` module generates a structured JSON plan, evaluating dependencies and step-by-step logic.
4. **Execution Phase**: The agent iterates through the plan, invoking the `ToolEngine` to read files, modify code, or run bash commands.
5. **Verification**: After execution, the agent checks the output (e.g., running tests). If a failure occurs, the agent loops back to fix the code autonomously.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Planning : User requests task
    Planning --> Execution : Plan approved/generated
    
    state Execution {
        [*] --> ToolCall
        ToolCall --> ToolResponse
        ToolResponse --> ToolCall : More steps needed
        ToolResponse --> Verification : Steps complete
    }
    
    Verification --> Success : Tests pass
    Verification --> Execution : Tests fail (Self-Correction)
    Success --> Idle
```

### 3.2 Model Routing & Quantum Fallbacks

Found in `kittycode/models/router.py` and `kittycode/quantum/router_q.py`, the routing system is designed to handle API failures, rate limits, and budget constraints without crashing. It features a unique **Quantum-Inspired Routing** algorithm written in pure Python.

#### Quantum-Inspired Routing Architecture
Instead of static fallback lists, KittyCode uses a probabilistic model inspired by quantum mechanics to select the best model for a specific task type (Chat, Code, Thought).

1. **Superposition**: Every available model is assigned a complex amplitude. The magnitude represents the model's health score (0-1), and the phase angle represents how well the model conceptually fits the current task (e.g., Code = 0 rad, Chat = 45 deg).
2. **Interference**: Recent successes or failures on similar tasks dynamically shift the phase of the models. Success causes constructive interference (boosting probability), while failure causes destructive interference.
3. **Amplitude Amplification**: A Grover-inspired algorithm reflects the amplitudes around the mean to exponentially boost the highest-scoring candidate relative to the others.
4. **Measurement**: The final model is selected by sampling the probability distribution (the Born rule: $|amplitude|^2$).

```mermaid
flowchart LR
    A[Available Models] -->|Health & Task Type| B(Superposition State)
    B -->|Recent Telemetry| C{Interference}
    C -->|Success| D[Constructive Phase Shift]
    C -->|Failure| E[Destructive Phase Shift]
    D --> F(Amplitude Amplification)
    E --> F
    F -->|Born Rule Measurement| G[Selected Model]
    
    style B fill:#2b2b2b,stroke:#8b5cf6
    style F fill:#2b2b2b,stroke:#8b5cf6
```

#### Health Tracking & Auto-Healing
- **Health Tracking**: The system tracks the latency and success rate of every model. If a model fails 3 times, it is marked as "Unhealthy" and its quantum amplitude approaches zero.
- **Auto-Healing Authentication**: If an API returns a `401 Unauthorized` (e.g., a bad key), the Router intercepts the error, pauses the loop, and prompts the user to re-run the setup wizard, preventing infinite crash loops.

### 3.3 Tool Engine & Sandbox Security

The `ToolEngine` (`kittycode/tools/engine.py`) exposes a specific set of tools to the LLM (e.g., `view_file`, `replace_file_content`, `run_command`).

**The Sandbox Validator (`security/sandbox.py`)** acts as the absolute gatekeeper:
- **Path Traversal Prevention**: Any tool call trying to access files outside the `PROJECT_ROOT` (e.g., `../../etc/passwd`) is immediately blocked.
- **Command Whitelisting**: Potentially destructive commands are flagged.
- **Security Patch 1.0**: The `kitty secure` command triggers the `audit_security_posture()` function, which scans for leaked API keys in log files, ensures the `.env` file is permission-locked, and verifies key integrity.

### 3.4 Structured Memory & The Cryptographic Vault

KittyCode remembers your preferences, architectural decisions, and common bugs using a local JSON-backed structured graph (`memory/manager.py`). 

To protect sensitive data extracted during autonomous operations, Kitty implements a zero-dependency **Cryptographic Vault** (`security/vault.py`).

#### Vault Cryptography Architecture
The Vault ensures that even if an attacker gains read access to the `.kitty/memory.json` file, they cannot extract sensitive facts without local execution context.

1. **Machine Fingerprinting**: The vault generates a stable machine identifier (e.g., reading SMBIOS UUID on Windows or `/etc/machine-id` on Linux).
2. **Key Derivation**: It applies **PBKDF2** (Password-Based Key Derivation Function 2) using HMAC-SHA256 with 200,000 iterations. It combines the machine ID and an optional user passphrase to generate a robust 32-byte cryptographic key.
3. **AES-256-GCM Encryption**: The derived key powers a Fernet symmetric encryption implementation to encrypt and decrypt sensitive memory nodes on the fly.

```mermaid
sequenceDiagram
    participant Agent
    participant Vault
    participant OS as Operating System
    participant Disk as memory.json
    
    Note over Vault, OS: Initialization Phase
    Vault->>OS: Request Machine UUID
    OS-->>Vault: Return Hardware Fingerprint
    Vault->>Vault: PBKDF2(UUID + Passphrase, iterations=200k)
    Vault->>Vault: Derive 256-bit AES Key
    
    Note over Agent, Disk: Runtime Phase
    Agent->>Vault: encrypt("sensitive_api_key_123")
    Vault->>Vault: AES-256-GCM Encryption
    Vault-->>Agent: gAAAAABm... encrypted_token
    Agent->>Disk: Save Graph Node
```

---

## 4. Workflows & Examples

### The Setup Wizard (`kitty setup`)
The onboarding process is designed to be fool-proof:
1. **Path Diagnostics**: Checks if `python/Scripts` is in the user's `PATH`. If not, it provides step-by-step Windows instructions.
2. **Aesthetics**: Selects terminal themes (Catgirl, Matrix, Dracula).
3. **Intelligence**: Securely requests and saves OpenRouter/Gemini API keys to `~/.kittycode/.env`.

### Chat Mode vs. Code Mode
- **Chat Mode**: Kitty acts as a standard conversational agent. She can read files to answer questions but will not execute modifying commands.
- **Code Mode**: Kitty assumes full autonomy. She will read, write, and execute commands (with your permission) to fulfill a complex task.

---

## 5. Developer & Contributor Guide

If you wish to contribute or modify KittyCode, here is the repository layout:

```text
kitty-CLI/
├── kittycode/               # Core Application Package
│   ├── agent/               # Autonomous logic, Planning, State machine
│   ├── cli/                 # Typer/Rich UI, Setup wizards, App entrypoint
│   ├── config/              # Settings, Environment parsing
│   ├── context/             # Codebase indexer, KITTY.md loader
│   ├── core/                # System prompts, Safety Critic
│   ├── memory/              # Graph storage, retrieval algorithms
│   ├── models/              # Model Router, OpenRouter/Gemini clients
│   ├── security/            # Sandbox, Audits, Encryption Vault
│   ├── telemetry/           # Real-time logging, metrics
│   └── tools/               # File readers, Writers, Git, AST tools
├── tests/                   # Pytest suite
├── pyproject.toml           # PEP 517 build configuration & dependencies
├── install.sh / .bat        # One-click installer scripts
└── README.md                # User landing page
```

**Development Requirements:**
- Python >= 3.9
- Run `pip install -e ".[dev]"` to install pytest, black, and mypy.
- Run tests via `python -m pytest`.
