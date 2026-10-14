# phase5_tester.py
import cv2
import numpy as np
import os
import sys
import time

try:
    import onnxruntime as ort
    from ultralytics import YOLO
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

print("=== PHASE 5 TESTER ===")
print("Testing core JARVIS modules...\n")

# ----------------------------
# 1️⃣ Camera Test
# ----------------------------
print("1️⃣ Testing Camera...")
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("❌ Cannot open camera")
else:
    ret, frame = cam.read()
    if ret:
        print("✅ Camera capture OK")
    else:
        print("❌ Failed to grab frame")
cam.release()

# ----------------------------
# 2️⃣ Face Detection Test
# ----------------------------
print("\n2️⃣ Testing Face Detection...")
face_prototxt = "jarvis_ai/models/deploy.prototxt"
face_caffemodel = "jarvis_ai/models/res10_300x300_ssd_iter_140000.caffemodel"

if os.path.exists(face_prototxt) and os.path.exists(face_caffemodel):
    face_net = cv2.dnn.readNetFromCaffe(face_prototxt, face_caffemodel)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    blob = cv2.dnn.blobFromImage(dummy_frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
    face_net.setInput(blob)
    detections = face_net.forward()
    print(f"✅ Face detection network loaded. Dummy detections: {detections.shape}")
else:
    print("❌ Face detection models missing")

# ----------------------------
# 3️⃣ Face Recognition Test (SFace) - FIXED
# ----------------------------
print("\n3️⃣ Testing Face Recognition (SFace)...")
sface_model_path = "jarvis_ai/models/face_recognition_sface_2021dec.onnx"

if os.path.exists(sface_model_path):
    session = ort.InferenceSession(sface_model_path)
    # Check the expected input name
    input_name = session.get_inputs()[0].name
    print(f"ONNX input name detected: {input_name}")  # should be 'data'

    dummy_input = np.random.rand(1, 3, 112, 112).astype(np.float32)
    embedding = session.run(None, {input_name: dummy_input})[0]
    print(f"✅ SFace loaded. Embedding shape: {embedding.shape}")
else:
    print("❌ SFace model missing")
# ----------------------------
# 4️⃣ YOLO Object Detection Test
# ----------------------------
print("\n4️⃣ Testing YOLOv8 Object Detection...")

yolo_model_path = "jarvis_ai/models/yolov8n.pt"

if os.path.exists(yolo_model_path):
    model = YOLO(yolo_model_path)

    test_img = "bus.jpg"

    results = model(test_img)

    # Show first result
    results[0].show()

    print("✅ YOLO loaded and detection working")

else:
    print("❌ YOLO model missing")
# ----------------------------
# 5️⃣ Vosk Offline Voice Recognition Test
# ----------------------------
print("\n5️⃣ Testing Vosk Offline Voice Recognition...")

vosk_model_path = "jarvis_ai/models/vosk-model"

if os.path.exists(vosk_model_path):
    try:
        model = Model(vosk_model_path)
        rec = KaldiRecognizer(model, 16000)
        print("✅ Vosk model loaded. Listening for 5 seconds...")

        def callback(indata, frames, time_, status):
            # Convert NumPy array to bytes for Vosk
            if rec.AcceptWaveform(indata.tobytes()):
                print("Full result:", rec.Result())
            else:
                print("Partial result:", rec.PartialResult())

        import sounddevice as sd
        import time

        with sd.InputStream(callback=callback, channels=1, samplerate=16000):
            time.sleep(5)

    except Exception as e:
        print(f"❌ Vosk test failed: {e}")

else:
    print("❌ Vosk model missing")

print("\n=== PHASE 5 TEST COMPLETE ===")
print("✅ All available modules have been tested.")