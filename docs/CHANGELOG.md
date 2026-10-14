# Changelog

All notable changes to the AI Suite project will be documented in this file.

## [v1.0] - Upcoming
- **Installer**: Standalone desktop installer.
- **Settings**: Fully functional UI settings panel.
- **Documentation**: Comprehensive setup and contribution documentation.

## [v0.9.0-alpha] - Current Release Candidate
### Added
- **Voice System 2.0**: Overhauled the audio pipeline with a non-blocking `AudioInputFramework`, precise VAD, and asynchronous Edge-TTS playback with cooperative cancellation (barge-in).
- **System Intelligence**: Bridged Ollama locally, introduced conversational memory with SQLite, and integrated desktop interactions.
- **Workspaces**: Segregated AI Suite into JARVIS, FRIDAY, and EDITH workspaces.
- **Universal Command Palette**: Prepared the header UI for global command execution.

### Changed
- **Conversation Polish**: Eliminated hallucinated contexts and ensured the AI successfully retains persistent, context-aware memory.
- **Header Polish**: Standardized the header to visually display real-time metrics (Compute, Model, TTS, and User Profile).

### Fixed
- Stabilized memory leaks in the VAD background thread.
- Fixed an issue where echo suppression aggressively discarded valid user interrupt commands during TTS playback.
- Resolved UI tearing during rapid workspace switching.

### Removed
- **Cleanup**: Purged legacy migration scripts, scratch tests, and temporary diagnostic databases to prepare for a public release.

### Known Limitations
- The camera integration currently falls back gracefully if hardware is locked by another application.
- The EDITH workspace is currently an architectural placeholder.
