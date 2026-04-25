# KittyCode CLI 🐈‍⬛

KittyCode is an advanced, local-first AI coding CLI and agentic co-pilot. It is engineered for maximum performance, offline resilience, and strict execution security. Recently upgraded with **pure-Python quantum-inspired heuristics**, KittyCode approaches model routing, task planning, and memory retrieval as mathematical probability optimizations rather than simple linear chains.

## Core Capabilities

- **Quantum-Inspired Architecture**: Uses amplitude amplification (Grover-style search) for memory retrieval, superposition for model routing, and simulated quantum annealing for structural task planning.
- **Strict Execution Sandbox**: All filesystem operations are contained. A robust `SafetyCritic` guards against path traversal, large payloads, and destructive shell operators.
- **Multi-Model Routing**: Native support for `OpenRouter`, `Bytez`, and `Gemini`. Models are continually health-checked, and routing dynamically adjusts based on success rates and latencies.
- **Debate & Validation Loop**: A dual-agent setup where a `Builder` creates plans and a `Critic` evaluates both the logic and the *execution logs* before generating the final output.
- **Graceful Offline Degradation**: Boots and operates locally even if API keys are missing or the network drops.
- **Incremental Interactive UI**: Optimized for speed and clarity, only re-rendering what's necessary to prevent flicker and duplication.

## Response Demo

![KittyCode Interactive UI Demo](file:///C:/Users/krish/.gemini/antigravity/brain/09d0fd77-4910-49bc-97b7-25fc952bec0c/kitty_ui_demo_1777154472662.png)

---

## Installation

KittyCode uses modern Python packaging (`pyproject.toml`).

**Basic Installation**
```bash
pip install -e .
```

**Install with Extras**
You can selectively install dependencies based on your needs:
- `pip install -e .[vector]` : Installs FAISS and Sentence Transformers for semantic memory embeddings.
- `pip install -e .[gemini]` : Installs the official `google-genai` SDK for Google's native API.
- `pip install -e .[all]` : Installs all optional extensions.

---

## Configuration

Set up your environment variables. KittyCode searches for `.env` files in `~/.kittycode/.env` (Global) and `./.env` (Project-specific).

```env
# Provider API Keys
BYTEZ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# Runtime Behavior (Optional)
KITTY_MEMORY_BACKEND=keyword     # Or 'vector' / 'auto'
KITTY_MEMORY_ALLOW_DOWNLOAD=1    # Allow downloading FAISS embedding models
KITTY_CMD_ALLOWLIST=python,pytest,git,ls,cat
```

---

## Usage & CLI Endpoints

KittyCode utilizes `Typer` and `Rich` to provide a beautiful, structured terminal interface. Add the `--json` flag to any command for programmatic integration.

### Interactive Mode
- `kitty` : Launches the interactive chat and command REPL.

### Diagnostics & Management
- `kitty doctor` : Comprehensive environment diagnostics, package checks, and API key validations.
- `kitty models` : View the routing table, model health scores, and latency metrics.
- `kitty stats` : View the observability dashboard with command latency and failure rates.
- `kitty config --set-theme matrix` : View and customize the UI theme.
- `kitty version` : Show installed version.

### Model Routing Control
- `kitty models --set-primary gpt-4.1` : Override the default primary model for the session.
- `kitty models --set-primary claude-sonnet --persist` : Persist the primary model choice to the local project state.
- `kitty models --show-chain Code` : Show the quantum-resolved routing chain for a specific task profile.
- `kitty models --reset --persist` : Revert all routing preferences to default.

### Memory & State Management
- `kitty memory list --limit 20` : List recent memory entries.
- `kitty memory add --key bug_42 --value "router timeout" --category bugs` : Inject a structured fact into memory.
- `kitty memory find "timeout bug"` : Quantum-assisted search against the memory context.
- `kitty memory prune --max 300 --dedupe` : Prune old and duplicate memories.
- `kitty memory export --path backup.json` : Export structured memory to a JSON payload.

### One-Shot Execution
- `kitty chat "explain this file"` : Fast, one-shot conversation response.
- `kitty run "analyze this repo"` : One-shot plan generation without executing.
- `kitty run "fix tests" --execute --yes` : Generate and execute a task queue non-interactively.

---

## Architecture

KittyCode's architecture is divided into discrete layers that prioritize security, deterministic routing, and structural planning.

### System Components

```mermaid
graph TD
    User([User CLI / REPL]) --> Agent[KittyAgent]
    
    subgraph Core Orchestration
        Agent --> Planner[Task Planner]
        Agent --> Debate[Debate Manager]
    end
    
    subgraph Quantum Layer
        Planner -.-> QA[Quantum Annealing]
        Router[Model Router] -.-> QS[Quantum Superposition]
        Memory[Memory Manager] -.-> QG[Grover Amplification]
    end
    
    subgraph External Models
        Router --> OR[OpenRouter]
        Router --> Bytez[Bytez]
        Router --> Gemini[Gemini]
    end
    
    subgraph Execution & Security
        Debate --> ToolEngine[Tool Engine]
        ToolEngine --> Safety[Safety Critic]
        ToolEngine --> Sandbox[Sandbox Validator]
        Safety --> FS[File System]
    end

    Agent --> Router
    Agent --> Memory
```

- **`kittycode/quantum`**: Mathematical optimization heuristics for routing, task annealing, and memory amplitude amplification.
- **`kittycode/agent`**: Contains the `KittyAgent`, `Planner`, and the `DebateManager` (Critic-Builder loop).
- **`kittycode/models`**: LLM integrations, provider classes, and the deterministic health tracker.
- **`kittycode/memory`**: Persistent, structured graph/vector memory system.
- **`kittycode/tools`**: File system tools and the strict `ToolEngine`.
- **`kittycode/security`**: The `SandboxValidator` isolating directory access and the `SafetyCritic` scanning for shell injection.
- **`kittycode/cli`**: Typer-based CLI endpoints, telemetry logic, and Rich console formatting.

### Execution Pipeline

The execution pipeline ensures that requests are heavily vetted, context is appropriately fetched, and the output is robustly debated before surfacing to the user or modifying the file system.

```mermaid
sequenceDiagram
    participant User
    participant CLI as Kitty CLI
    participant Agent as KittyAgent
    participant Mem as MemoryManager
    participant Plan as Planner
    participant Debate as DebateManager
    participant Tools as ToolEngine

    User->>CLI: Prompt (e.g. "Fix tests")
    CLI->>Agent: Route Request
    Agent->>Mem: quantum_retrieve(context)
    Mem-->>Agent: Amplified Context
    Agent->>Plan: generate_plan(Prompt + Context)
    Plan->>Plan: quantum_anneal_steps()
    Plan-->>Agent: Task Queue
    
    loop Over Task Queue
        Agent->>Debate: run_step(Task)
        
        loop Builder-Critic Debate
            Debate->>Debate: Builder Drafts Output
            Debate->>Tools: Propose Tools
            Tools-->>Debate: Tool Execution Logs
            Debate->>Debate: Critic Evaluates Logs + Output
        end
        
        Debate-->>Agent: Verified Result
    end
    
    Agent-->>CLI: Final Response
    CLI-->>User: Output
```

1. **Context Retrieval**: User input is paired with historical graph memory. The quantum Grover pre-filter ensures the most relevant vectors are elevated.
2. **Task Planning**: The raw prompt is split into atomic components. The Quantum Annealing scheduler reorganizes these tasks to ensure reasoning logic precedes execution.
3. **Debate Loop**: For each atomic task, a Builder model executes logic/tools. A separate Critic model reviews the resulting Tool execution logs and output to confirm no hallucinatory logic or boundary violations occurred.
4. **Final Response**: Upon Critic approval, the task succeeds, state updates, and the user receives the final formatted output.

---

## Security Policies

- **Subprocess Guardrails**: Terminal commands executed via `run_cmd` are strictly timed out (60s) and screened against a predefined blocked patterns list (e.g., `rm -rf`, `&&`, `;`).
- **Path Confinement**: All tool actions require absolute paths validated against the `SandboxValidator`, ensuring no traversal (`../`) escapes the project boundaries.
- **Observability**: Execution errors and structural exceptions are piped to local `.kitty/` JSON logs for safe post-mortem review.
