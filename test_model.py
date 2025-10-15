"""Quick script to test the person detection model."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import torch
from ml.models.person_classifier import PersonClassifierModel

# Check if checkpoint exists
checkpoint_path = Path("artifacts/person-classifier/checkpoints/latest.pth")

if not checkpoint_path.exists():
    print(f"❌ No checkpoint found at {checkpoint_path}")
    print("Please train the model first using the dashboard.")
    sys.exit(1)

print(f"✅ Loading checkpoint from {checkpoint_path}")

# Load the model
model = PersonClassifierModel.load(checkpoint_path, device="cpu")

print(f"\n📊 Model Metadata:")
for key, value in model.metadata.items():
    print(f"  {key}: {value}")

print(f"\n✅ Model loaded successfully!")
print(f"Device: {model.device}")

# Test prediction on a sample image
from PIL import Image
import os

# Find first image in dataset
image_dir = Path("data/processed/person_images")
if image_dir.exists():
    images = list(image_dir.glob("*.jpg"))[:3]
    if images:
        print(f"\n🧪 Testing on sample images:")
        for img_path in images:
            try:
                img = Image.open(img_path)
                label, confidence = model.predict(img)
                print(f"  {img_path.name}: {label} (confidence: {confidence:.3f})")
            except Exception as e:
                print(f"  {img_path.name}: Error - {e}")
    else:
        print("\n⚠️ No test images found")
