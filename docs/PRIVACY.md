# Privacy Policy

AI Suite was built from the ground up to guarantee absolute privacy and operational security. 

## 1. Local-First Architecture
AI Suite runs locally on your hardware. Core intelligence routing, vision analysis, and audio processing execute entirely within the boundaries of your local machine. 

## 2. Telemetry and Analytics
- **No Telemetry**: We do not collect, monitor, or harvest system usage data.
- **No Analytics**: We do not track feature utilization or crash logs externally.
- **No Advertisements**: The application will never serve ads or promotional content.

## 3. Data Storage
- **No Cloud Storage**: Conversations, memories, and screen interactions are never synced to the cloud.
- **Local Persistence**: AI Suite uses a local SQLite database (`jarvis_memory.sqlite3`) to retain contextual conversation memory. You can delete this file at any time to wipe your profile.

## 4. Hardware Access
- **Camera**: The camera is accessed *only* when the vision module is explicitly enabled. Snapshots are processed entirely in memory via YOLO and are not uploaded to external servers.
- **Microphone**: The microphone is accessed *only* when the voice module is enabled. VAD and STT processing happen strictly offline via the local Vosk backend.

## 5. Third-Party Services
While intelligence and sensing remain local, the TTS (Text-to-Speech) engine defaults to `Edge-TTS` for high-fidelity voice output. This service routes text to Microsoft endpoints. If absolute air-gapped functionality is required, you must configure a local TTS backend. Nothing is ever uploaded unless explicitly requested or inherently required by a service you configure.
