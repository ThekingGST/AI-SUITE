"""V2 Performance Baseline Measurement Script.

Records pre-optimization metrics for GPU/VRAM/CPU/RAM usage,
model load times, and inference latencies.

Run from project root: python tests/baseline_measurement.py
"""

import sys
import os
import time
import json
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def measure_system_resources():
    """Measure idle system resources."""
    import psutil
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()
    sys_mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1.0)
    
    return {
        "process_rss_mb": round(mem.rss / 1024**2, 2),
        "system_ram_total_gb": round(sys_mem.total / 1024**3, 2),
        "system_ram_available_gb": round(sys_mem.available / 1024**3, 2),
        "system_ram_used_percent": sys_mem.percent,
        "cpu_percent": cpu_percent,
    }


def measure_gpu():
    """Measure GPU state."""
    result = {
        "gpu_available": False,
        "gpu_name": "N/A",
        "vram_total_mb": 0,
        "vram_used_mb": 0,
        "vram_free_mb": 0,
        "gpu_utilization_percent": 0,
        "gpu_temperature_c": 0,
        "driver_version": "N/A",
    }
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        driver = pynvml.nvmlSystemGetDriverVersion()
        
        result.update({
            "gpu_available": True,
            "gpu_name": name,
            "vram_total_mb": round(meminfo.total / 1024**2, 2),
            "vram_used_mb": round(meminfo.used / 1024**2, 2),
            "vram_free_mb": round(meminfo.free / 1024**2, 2),
            "gpu_utilization_percent": util.gpu,
            "gpu_temperature_c": temp,
            "driver_version": driver,
        })
        pynvml.nvmlShutdown()
    except Exception as e:
        result["error"] = str(e)
    return result


def measure_pytorch_cuda():
    """Measure PyTorch CUDA availability."""
    result = {
        "pytorch_cuda_available": False,
        "pytorch_cuda_device_count": 0,
        "pytorch_cuda_device_name": "N/A",
        "pytorch_cuda_version": "N/A",
        "pytorch_version": "N/A",
    }
    try:
        import torch
        result["pytorch_version"] = torch.__version__
        result["pytorch_cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            result["pytorch_cuda_device_count"] = torch.cuda.device_count()
            result["pytorch_cuda_device_name"] = torch.cuda.get_device_name(0)
            result["pytorch_cuda_version"] = torch.version.cuda or "N/A"
    except Exception as e:
        result["error"] = str(e)
    return result


def measure_onnx_providers():
    """Measure ONNX Runtime execution providers."""
    result = {
        "onnx_providers": [],
        "onnx_version": "N/A",
    }
    try:
        import onnxruntime as ort
        result["onnx_version"] = ort.__version__
        result["onnx_providers"] = ort.get_available_providers()
    except Exception as e:
        result["error"] = str(e)
    return result


def measure_yolo_load():
    """Measure YOLO model load time and inference."""
    result = {
        "yolo_load_time_s": 0,
        "yolo_device": "N/A",
        "yolo_inference_time_ms": 0,
        "yolo_loaded": False,
    }
    try:
        import numpy as np
        from jarvis_ai.config import MODELS_DIR
        model_path = MODELS_DIR / "yolov8n.pt"
        if not model_path.exists():
            result["error"] = f"Model not found: {model_path}"
            return result
        
        from ultralytics import YOLO
        import torch
        
        t0 = time.perf_counter()
        model = YOLO(str(model_path))
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        model.to(device)
        t1 = time.perf_counter()
        
        result["yolo_load_time_s"] = round(t1 - t0, 3)
        result["yolo_device"] = str(model.device)
        result["yolo_loaded"] = True
        
        # Warm-up inference
        dummy = np.random.randint(0, 255, (540, 960, 3), dtype=np.uint8)
        model.predict(dummy, conf=0.38, verbose=False)
        
        # Timed inference (average of 5)
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            model.predict(dummy, conf=0.38, verbose=False)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        
        result["yolo_inference_time_ms"] = round(sum(times) / len(times), 2)
        
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception as e:
        result["error"] = str(e)
    return result


def measure_sface_load():
    """Measure SFace ONNX model load time and inference."""
    result = {
        "sface_load_time_s": 0,
        "sface_providers": [],
        "sface_inference_time_ms": 0,
        "sface_loaded": False,
    }
    try:
        import numpy as np
        import onnxruntime as ort
        from jarvis_ai.config import MODELS_DIR
        model_path = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
        if not model_path.exists():
            result["error"] = f"Model not found: {model_path}"
            return result
        
        available = ort.get_available_providers()
        providers = []
        if "CUDAExecutionProvider" in available:
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")
        
        t0 = time.perf_counter()
        session = ort.InferenceSession(str(model_path), providers=providers)
        t1 = time.perf_counter()
        
        result["sface_load_time_s"] = round(t1 - t0, 3)
        result["sface_providers"] = session.get_providers()
        result["sface_loaded"] = True
        
        # Warm-up + timed inference
        input_name = session.get_inputs()[0].name
        dummy = np.random.randn(1, 3, 112, 112).astype(np.float32)
        session.run(None, {input_name: dummy})
        
        times = []
        for _ in range(10):
            t0 = time.perf_counter()
            session.run(None, {input_name: dummy})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        
        result["sface_inference_time_ms"] = round(sum(times) / len(times), 2)
    except Exception as e:
        result["error"] = str(e)
    return result


def measure_ollama():
    """Check Ollama status and GPU usage."""
    result = {
        "ollama_running": False,
        "ollama_models": [],
        "ollama_gpu_layers": "unknown",
    }
    try:
        import urllib.request
        # Check server
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            result["ollama_running"] = True
            result["ollama_models"] = [m["name"] for m in data.get("models", [])]
        
        # Check GPU usage via /api/ps
        try:
            req2 = urllib.request.Request("http://localhost:11434/api/ps")
            with urllib.request.urlopen(req2, timeout=3) as resp2:
                ps_data = json.loads(resp2.read())
                running = ps_data.get("models", [])
                if running:
                    for m in running:
                        gpu_layers = m.get("size_vram", 0)
                        total_size = m.get("size", 0)
                        if gpu_layers > 0:
                            result["ollama_gpu_layers"] = f"{gpu_layers}/{total_size} bytes on GPU"
                        else:
                            result["ollama_gpu_layers"] = "CPU only"
                else:
                    result["ollama_gpu_layers"] = "no models loaded"
        except Exception:
            pass
    except Exception as e:
        result["error"] = str(e)
    return result


def main():
    print("=" * 60)
    print("  AI Suite V2 — Performance Baseline Measurement")
    print("=" * 60)
    
    baseline = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": "PRE-OPTIMIZATION (V1 baseline)",
    }
    
    print("\n[1/6] Measuring system resources...")
    baseline["system"] = measure_system_resources()
    print(f"  RAM: {baseline['system']['process_rss_mb']} MB (process)")
    print(f"  System RAM: {baseline['system']['system_ram_used_percent']}% used")
    print(f"  CPU: {baseline['system']['cpu_percent']}%")
    
    print("\n[2/6] Measuring GPU...")
    baseline["gpu"] = measure_gpu()
    if baseline["gpu"]["gpu_available"]:
        print(f"  GPU: {baseline['gpu']['gpu_name']}")
        print(f"  VRAM: {baseline['gpu']['vram_used_mb']} / {baseline['gpu']['vram_total_mb']} MB")
        print(f"  GPU Util: {baseline['gpu']['gpu_utilization_percent']}%")
        print(f"  Temp: {baseline['gpu']['gpu_temperature_c']}C")
        print(f"  Driver: {baseline['gpu']['driver_version']}")
    else:
        print(f"  No NVIDIA GPU detected: {baseline['gpu'].get('error', 'N/A')}")
    
    print("\n[3/6] Measuring PyTorch CUDA...")
    baseline["pytorch"] = measure_pytorch_cuda()
    print(f"  PyTorch: {baseline['pytorch']['pytorch_version']}")
    print(f"  CUDA Available: {baseline['pytorch']['pytorch_cuda_available']}")
    if baseline["pytorch"]["pytorch_cuda_available"]:
        print(f"  CUDA Device: {baseline['pytorch']['pytorch_cuda_device_name']}")
        print(f"  CUDA Version: {baseline['pytorch']['pytorch_cuda_version']}")
    
    print("\n[4/6] Measuring ONNX Runtime...")
    baseline["onnx"] = measure_onnx_providers()
    print(f"  ONNX Version: {baseline['onnx']['onnx_version']}")
    print(f"  Providers: {baseline['onnx']['onnx_providers']}")
    
    print("\n[5/6] Measuring YOLO (load + inference)...")
    baseline["yolo"] = measure_yolo_load()
    if baseline["yolo"]["yolo_loaded"]:
        print(f"  Load Time: {baseline['yolo']['yolo_load_time_s']}s")
        print(f"  Device: {baseline['yolo']['yolo_device']}")
        print(f"  Inference: {baseline['yolo']['yolo_inference_time_ms']}ms avg")
    else:
        print(f"  YOLO failed: {baseline['yolo'].get('error', 'unknown')}")
    
    # Re-measure resources after model loads
    baseline["system_after_models"] = measure_system_resources()
    baseline["gpu_after_models"] = measure_gpu()
    print(f"\n  RAM after models: {baseline['system_after_models']['process_rss_mb']} MB")
    if baseline["gpu_after_models"]["gpu_available"]:
        print(f"  VRAM after models: {baseline['gpu_after_models']['vram_used_mb']} MB")
    
    print("\n[6/6] Measuring SFace ONNX (load + inference)...")
    baseline["sface"] = measure_sface_load()
    if baseline["sface"]["sface_loaded"]:
        print(f"  Load Time: {baseline['sface']['sface_load_time_s']}s")
        print(f"  Active Providers: {baseline['sface']['sface_providers']}")
        print(f"  Inference: {baseline['sface']['sface_inference_time_ms']}ms avg")
    else:
        print(f"  SFace failed: {baseline['sface'].get('error', 'unknown')}")
    
    print("\n[BONUS] Checking Ollama...")
    baseline["ollama"] = measure_ollama()
    print(f"  Running: {baseline['ollama']['ollama_running']}")
    if baseline["ollama"]["ollama_running"]:
        print(f"  Models: {baseline['ollama']['ollama_models']}")
        print(f"  GPU: {baseline['ollama']['ollama_gpu_layers']}")
    
    # Final resource snapshot
    baseline["system_final"] = measure_system_resources()
    baseline["gpu_final"] = measure_gpu()
    
    # Save results
    output_path = project_root / "tests" / "baseline_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, default=str)
    
    print(f"\n{'=' * 60}")
    print(f"  Baseline saved to: {output_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
