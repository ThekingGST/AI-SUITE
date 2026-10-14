# Contributing to AI Suite

Thank you for your interest in improving AI Suite! We welcome community contributions ranging from bug fixes to entirely new intelligence plugins.

## Repository Structure
- `ai_suite/` - Core bootstrapping and shared application framework.
- `jarvis_ai/` - The Personal Assistant workspace (Voice, Vision, Automation).
- `friday_ai/` - The AI IDE workspace (File system analysis, Development loops).
- `shared/` - Common utilities, models, and UI components.

## Development Workflow
1. **Fork & Clone**: Fork the repository and clone it locally.
2. **Setup**: Follow the instructions in `SETUP.md` to configure your virtual environment and dependencies.
3. **Branch Strategy**: Create a feature branch off `main` (e.g., `feature/voice-improvements` or `fix/ui-tearing`).
4. **Develop**: Ensure you adhere to the project's coding standards.

## Coding Standards
- **Python**: Use Python 3.11 features. We heavily utilize Type Hinting (`-> str`, `dict[str, Any]`).
- **Formatting**: Adhere to standard PEP8 formatting. 
- **Docstrings**: Provide Google-style docstrings for any core interface, manager, or complex pipeline.
- **UI**: Keep logic out of UI components. Use Qt Signals and Slots to communicate between the backend workers and the frontend display.

## Commit Style
Write clean, descriptive commit messages. 
- **Good**: `Fix echo suppression bug in voice listener`
- **Bad**: `Fixed bug`

## Pull Requests
- Ensure your code does not break the `python ai_suite/main.py` boot sequence.
- Describe your changes in detail in the PR.
- If it's a UI change, provide screenshots.

## Issues
Before opening an issue, please check if a similar issue already exists. When opening an issue, provide steps to reproduce, system specifications, and relevant logs.
