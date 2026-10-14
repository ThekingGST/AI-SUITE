# Release Notes

## AI Suite v0.9.0-alpha

AI Suite transitions from a development concept to a polished Alpha release candidate. 

### Major Milestones Achieved
1. **Voice System 2.0 Integration**: We completely eliminated audio blocking by decoupling PyAudio streams from the STT and TTS backends. Users can now barge in on TTS playback instantly using standard emergency keywords ("stop", "cancel", "quiet").
2. **Local-First Intelligence**: Ollama is now deeply baked into the application via an abstraction layer that ensures context windows are managed strictly on-device using SQLite memory tables.
3. **Professionalization**: The repository has undergone a massive engineering cleanup sprint, removing temporary logs, scratch files, and establishing a robust documentation standard.

### Migration Notes
- If you used previous developmental builds, ensure you delete your old `.venv` and run a fresh `pip install -r requirements.txt`.
- Existing `jarvis_memory.sqlite3` databases will gracefully migrate to the new schemas.

Thank you to all contributors who helped mature AI Suite to this alpha phase!
