# FAQ

### Does AI Suite work offline?
Yes. The core application runs locally using Ollama for intelligence, Vosk for Speech-To-Text (STT), and YOLO for computer vision. The only component that defaults to a cloud service is Microsoft Edge-TTS for high-quality voice synthesis. If you require a 100% air-gapped system, you can swap the TTS engine to a local backend in the settings.

### Does it require Ollama?
Yes. AI Suite uses Ollama as its primary backend inference engine for generating LLM responses locally.

### Does it send my data anywhere?
No. AI Suite does not collect telemetry, analytics, or usage statistics. Your camera snapshots, microphone input, and conversation history never leave your local machine (with the aforementioned exception of Edge-TTS sending text for synthesis).

### Can I disable the microphone?
Yes. You can toggle the microphone on and off directly from the user interface.

### Can I disable the camera?
Yes. The vision module can be disabled completely through the UI. If disabled, AI Suite will not capture or process any visual information.

### Can I use only FRIDAY?
Yes. While JARVIS is the default assistant workspace, you can seamlessly switch to the FRIDAY AI IDE workspace directly from the sidebar. Workspaces are strictly isolated.

### Can I change the voice?
Yes. The default voice is `en-US-AriaNeural`, but you can reconfigure this to any Edge-TTS compatible voice or swap to a local TTS backend entirely.

### Does CUDA improve performance?
Yes, dramatically. Running AI Suite with a CUDA-enabled NVIDIA GPU accelerates both Ollama (LLM text generation) and YOLO (vision object detection). While CPU-only mode is supported, response latency will be higher.

### What operating systems are supported?
AI Suite currently supports **Windows 10** and **Windows 11**. MacOS and Linux are not officially supported at this time due to specialized integrations with the Windows Audio API for zero-latency TTS barge-in and volume control.
