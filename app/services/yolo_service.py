import os
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO
import io

# Load YOLOv8 model — this is your teammate's custom-trained wildlife
# model, NOT the stock Ultralytics download, even though it shares the
# filename "my_model.pt".
MODEL_PATH = "my_model.pt"

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Custom wildlife model not found at {MODEL_PATH}. "
        f"Make sure my_model.pt is placed next to yolo_service.py."
    )

model = YOLO(MODEL_PATH)

# ✅ Fully dynamic — derived directly from the loaded model, every time.
# This was previously a hardcoded 10-item COCO-style list, which silently
# filtered out every species your custom model actually knows (tiger,
# leopard, wolf, rhinoceros, etc.) because they weren't in that list.
# Since this model is wildlife-only, every class it knows IS a wildlife
# class — no manual allow-list needed.
WILDLIFE_CLASSES = list(model.names.values())

print(f"✅ Loaded YOLO model from {MODEL_PATH}")
print(f"✅ Model classes ({len(WILDLIFE_CLASSES)}): {WILDLIFE_CLASSES}")

CONFIDENCE_THRESHOLD = 0.40  # 40% minimum confidence

def detect_wildlife(image_bytes: bytes) -> dict:
    """
    Run YOLOv8 detection on image bytes.
    Returns detection result with species, confidence, and verification status.
    """
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Convert to numpy array for YOLO
        img_array = np.array(image)
        
        # Run detection
        results = model(img_array, verbose=False)
        
        best_detection = None
        highest_confidence = 0.0

        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = model.names[class_id]

                # ✅ No allow-list filter — every class this model can
                # output is already a wildlife class.
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_detection = {
                        "species_detected": class_name,
                        "confidence": round(confidence, 4),
                        "is_verified": confidence >= CONFIDENCE_THRESHOLD,
                        "is_suspicious": confidence < CONFIDENCE_THRESHOLD
                    }

        # No wildlife detected
        if not best_detection:
            return {
                "species_detected": None,
                "confidence": 0.0,
                "is_verified": False,
                "is_suspicious": True,
                "message": "No wildlife detected in image"
            }

        best_detection["message"] = (
            f"Detected {best_detection['species_detected']} "
            f"with {best_detection['confidence']*100:.1f}% confidence"
        )
        return best_detection

    except Exception as e:
        return {
            "species_detected": None,
            "confidence": 0.0,
            "is_verified": False,
            "is_suspicious": True,
            "message": f"Detection error: {str(e)}"
        }


def generate_image_hash(image_bytes: bytes) -> str:
    """Generate a simple hash to detect duplicate image submissions."""
    import hashlib
    return hashlib.md5(image_bytes).hexdigest()