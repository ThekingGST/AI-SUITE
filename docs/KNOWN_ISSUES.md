# Known Issues

While AI Suite v1.0 is stable, it is an evolving project. Below are the known limitations and areas under active development:

- **Vision System is Experimental**: The visual processing pipeline utilizing YOLO for contextual memory and screen-awareness is still under active development. High-motion environments may cause processing delays.
- **Windows-Only Automation**: Several desktop automation features, audio routing mechanisms, and hardware hooks rely on Windows-specific APIs. Support for Linux and macOS is not currently on the immediate roadmap.
- **Hardware Acceleration Requires CUDA**: Certain GPU-accelerated modules, notably PyTorch vision operations, rely strictly on NVIDIA CUDA. Systems with AMD or Intel GPUs will fall back to CPU execution, which may result in higher latency.
- **Face Registration Required**: The dynamic face tracking module requires initial user registration. Unregistered faces will be categorized generally.
- **Initial Boot Time**: The first launch of the application may take an extended period while Ollama allocates VRAM, initializes the LLM context, and pre-warms the Vosk acoustic models.
- **EDITH Workspace Architecture**: The EDITH Security Suite is currently just an architectural placeholder awaiting full implementation in v2.0.

*We are actively tracking these limitations and planning improvements. If you encounter bugs beyond these constraints, please review our contribution guidelines and open an issue.*
