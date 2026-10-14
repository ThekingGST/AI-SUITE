# AI Suite Setup Guide

## 1. Prerequisites
Ensure your operating system is **Windows 10/11** or a supported **Linux** distribution. While Windows provides deeper desktop integrations out-of-the-box, Linux is fully supported for backend and inference operations.

### Python
You must have **Python 3.11** installed. (Avoid Python 3.12+ temporarily due to PyAudio and Pygame compatibility issues).
Ensure `Add to PATH` is checked during installation.

### Virtual Environment
We strongly recommend using a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

## 2. Dependencies
Install the required dependencies using pip:
```bash
pip install -r requirements.txt
```

## 3. Ollama Installation & Model Download
AI Suite relies on [Ollama](https://ollama.com) for its local LLM capabilities.
1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Open a terminal and download the recommended model:
```bash
ollama run llama3
```

## 4. OpenRouter Configuration (Optional)
If you wish to use cloud models via OpenRouter (supported within the FRIDAY workspace), configure your API key:
1. Copy `.env.example` to `.env`.
2. Add your API key:
```ini
OPENROUTER_API_KEY=your_key_here
```
Note: Ensure `.env` is never committed to version control.

## 5. CUDA Setup (Optional but highly recommended)
If you have an NVIDIA GPU, ensure your CUDA Toolkit is installed and properly configured in your environment path to allow the Intelligence Framework and YOLO vision to utilize GPU acceleration. PyTorch will automatically use CUDA if available.

## 6. Running AI Suite
Once dependencies are met, start the application:
```bash
python ai_suite/main.py
```

## 7. Troubleshooting
### Microphone Not Detected
- Ensure your default microphone is properly set in Windows Sound Settings.
- Grant microphone permissions to Python in Windows Privacy Settings.
- If using Vosk, ensure the `vosk-model` directory is correctly placed in `jarvis_ai/models/`.

### Camera Not Working
- Ensure no other applications are locking your webcam (e.g., Zoom, OBS).
- The suite falls back gracefully, but vision features will be disabled if the camera fails.

### GPU Not Utilized
- Run `python -c "import torch; print(torch.cuda.is_available())"`. If this returns `False`, your PyTorch installation does not match your CUDA version. Reinstall PyTorch using the official matrix.

### Edge-TTS Errors
- Ensure you have an active internet connection (Edge-TTS requires network access, unlike the local STT or LLM components).

### Common Errors
- `ModuleNotFoundError`: Ensure your virtual environment is activated before running `main.py`.
- `sqlite3.DatabaseError`: If your local database is corrupted, safely delete `jarvis_memory.sqlite3` and restart.
