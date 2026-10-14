# Security

We take the security of your local environment seriously. AI Suite acts as an agentic framework capable of observing your screen and executing commands. It is inherently a privileged application.

## Local-First Guarantee
AI Suite is a local-first architecture. We rely on local Ollama execution to ensure that proprietary code, personal conversations, and on-screen data never leave your internal network boundaries.

## Permissions

### Microphone & Camera
AI Suite requires OS-level permissions to access your microphone and camera. These are strictly used for voice interaction and visual contextual awareness. The user retains full control to toggle these hardware inputs via the UI.

### Local File Access
FRIDAY (the AI IDE workspace) requires extensive local file access to read, parse, and modify your codebases. AI Suite assumes trust within the directories it is launched from or directed to.

## Credential Storage & API Key Handling
Currently, AI Suite does not orchestrate remote API keys by default, as the intelligence layer relies on Ollama. 
However, for future integrations, AI Suite will never store API keys in plaintext in the codebase. Users will be required to provide `.env` files or utilize local environment variables.
**Future Plans**: We are evaluating local vault encryption to securely store API keys used by automation plugins.

## Known Security Assumptions
AI Suite operates under the assumption that the local user account running the application is trusted.
There is currently no sandbox around the automation execution layer (Terminal). If an LLM is directed to execute a script, it will execute with the permissions of the user running AI Suite.

## Responsible Disclosure
If you find a vulnerability that could allow arbitrary remote code execution, unauthorized data exfiltration, or a sandbox escape in the application architecture, please report it via the GitHub Security Advisory tab.
