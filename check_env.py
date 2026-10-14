import sys
import torch
import os
import onnxruntime as ort
from pathlib import Path

def print_env():
    print(f"Python: {sys.version}")
    try:
        import faster_whisper
        print(f"faster-whisper: {faster_whisper.__version__}")
    except ImportError:
        print("faster-whisper: NOT INSTALLED")
        
    try:
        import lingua
        print("lingua: INSTALLED")
    except ImportError:
        print("lingua: NOT INSTALLED")
        
    print(f"torch CUDA: {torch.cuda.is_available()}")
    print(f"ONNX Providers: {ort.get_available_providers()}")
    
    models_dir = Path("D:/Coding/Jarvis/models")
    print(f"\nModels directory: {models_dir}")
    
    expected = [
        "tts/kokoro/kokoro-v1.0.onnx",
        "tts/kokoro/voices.json",
        "tts/piper/en_US-lessac-medium.onnx",
        "tts/piper/hi_IN-swara-medium.onnx",
        "tts/piper/te_IN-padmavathi-medium.onnx",
        "yolov8n.pt",
        "emotion_ferplus.onnx"
    ]
    
    for f in expected:
        path = models_dir / f
        print(f"{f}: {'EXISTS' if path.exists() else 'MISSING'}")

if __name__ == '__main__':
    print_env()
