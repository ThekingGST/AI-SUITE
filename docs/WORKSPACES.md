# AI Suite Workspaces

AI Suite utilizes a modular "Workspace" paradigm. Instead of having one monolithic AI that tries to be everything, you interact with specialized cognitive layers tailored for specific tasks.

## The Three Core Workspaces

### 1. JARVIS (Personal Assistant)
- **Role**: General automation, daily conversational agent.
- **Tools**: OS terminal execution, Python macro execution, Web searching.
- **Context**: Has access to desktop vision via screenshots.
- **Location**: `jarvis_ai/`

### 2. FRIDAY (AI IDE)
- **Role**: Deep codebase analysis, autonomous coding, error debugging.
- **Tools**: AST parsers, Linter integration, GitHub API integration.
- **Context**: Deeply embedded into your active project directories.
- **Location**: `friday_ai/`

### 3. EDITH (Security Analyst - Coming Soon)
- **Role**: Local threat detection, network traffic analysis.
- **Tools**: Wireshark integration, port scanning, anomaly detection.

## Adding a Custom Workspace

To add a new workspace to AI Suite:

1. Create a new directory in the project root (e.g., `my_workspace/`).
2. Create a class inheriting from `BaseWorkspace` (from `ai_suite.ui.workspace.base_workspace`).
3. Implement `setup_ui()`, `on_activate()`, and `on_deactivate()`.
4. Register the workspace in `ai_suite/ui/shell.py` using `WorkspaceManager.register_workspace()`.

Workspaces are completely sandboxed. They have their own system prompts, their own conversational memory, and their own UI layout inside the central QStackedLayout.
