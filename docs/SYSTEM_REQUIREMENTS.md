# System Requirements

AI Suite is designed to run locally, prioritizing privacy and zero-latency access to local hardware.

## Operating System
**Supported OS**: Windows 10 / Windows 11
*Linux and macOS are currently unsupported due to deep Windows API integrations for audio routing.*

## Hardware Specifications

### CPU
- **Minimum**: Modern Quad-Core Processor (Intel i5 8th Gen / Ryzen 3)
- **Recommended**: 8-Core Processor (Intel i7 12th Gen / Ryzen 7)

### RAM
- **Minimum**: 16 GB (Allows running a 4B parameter model with the UI)
- **Recommended**: 32 GB (Allows running 8B parameter models seamlessly alongside development tasks)

### GPU & CUDA
- **Minimum**: CPU-only mode is supported but will result in slower LLM response times.
- **Recommended**: NVIDIA GPU with at least 8GB VRAM (e.g., RTX 3060, RTX 4050, or better).
- **CUDA**: CUDA 11.8+ or 12.1+ is highly recommended for PyTorch hardware acceleration.

### Disk Space
- **Application**: < 500 MB
- **Models**: ~5 GB for Llama 3 (8B) + ~1 GB for Vosk/YOLO models.
- **Minimum Free Space**: 10 GB

## Internet Requirements & Offline Capabilities
- **LLM / VAD / STT / Vision**: Fully offline. 
- **TTS**: Requires internet access (Edge-TTS). 
- AI Suite is fully functional offline if the Edge-TTS backend is swapped for a local alternative, or if you only rely on text/visual outputs.

## Optional Dependencies
- Node.js (For specific FRIDAY web automation tests)
- C++ Build Tools (If recompiling native PyAudio extensions)
