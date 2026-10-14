import sys
import traceback
import os

def log(msg):
    print(msg, flush=True)

try:
    log("Loading torch...")
    import torch
    log(" [OK] torch loaded.")

    log("Loading PyQt5...")
    from PyQt5.QtWidgets import QApplication
    log(" [OK] PyQt5 loaded.")
    
    log("Loading numpy...")
    import numpy as np
    log(" [OK] numpy loaded.")
    
    log("Loading scipy...")
    import scipy
    log(" [OK] scipy loaded.")
    
    log("Loading cv2...")
    import cv2
    log(" [OK] cv2 loaded.")
    
    log("Loading sklearn...")
    import sklearn
    log(" [OK] sklearn loaded.")
    
    log("Loading onnxruntime...")
    import onnxruntime
    log(" [OK] onnxruntime loaded.")
    
    log("Loading ultralytics...")
    import ultralytics
    log(" [OK] ultralytics loaded.")
    
    log("\nAll native dependencies loaded successfully!")
    sys.exit(0)
    
except Exception as e:
    log(f"\n[FAIL] Import failed:")
    traceback.print_exc()
    sys.exit(1)
