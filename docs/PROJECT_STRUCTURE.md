# Project Structure

AI Suite is designed with strict modularity, separating core orchestration logic from individual workspace implementations.

```text
d:/Coding/Jarvis/
├── ai_suite/               # Core bootstrap and application orchestrator
│   ├── ui/                 # Shared UI frameworks (Header, Sidebar, Containers)
│   ├── main.py             # Primary entry point
│   └── launcher.py         # Subprocess manager for hardware hooks
├── jarvis_ai/              # The JARVIS Workspace (Personal Assistant)
│   ├── core/               # JARVIS-specific managers (Memory, Logic)
│   ├── ui/                 # JARVIS specific GUI widgets
│   ├── voice/              # Voice System 2.0 (VAD, STT, TTS, Pipelines)
│   ├── vision/             # YOLO processing and Screen Capture Memory
│   └── data/               # Local persistence (Faces, DBs)
├── friday_ai/              # The FRIDAY Workspace (AI IDE)
│   ├── services/           # Codebase analysis, LSPs, CLI integrations
│   └── ui/                 # Code editor panels, terminal outputs
├── shared/                 # Common dependencies across all workspaces
│   ├── models/             # Shared dataclasses and schemas
│   └── utils/              # Standard logging and file helpers
├── docs/                   # Documentation and Release artifacts
│   ├── development/        # Legacy plans and dev-logs
│   └── reports/            # Historic engineering audits
├── tests/                  # Unit and integration tests
├── assets/                 # Shared icons and fonts
├── README.md               # Overview
└── requirements.txt        # Python dependencies
```

### Extending the Suite
To create a new workspace (e.g., EDITH), you simply replicate the `jarvis_ai` or `friday_ai` structure, register your primary container in `ai_suite/main.py`, and hook into the shared `AssistantManager`.
