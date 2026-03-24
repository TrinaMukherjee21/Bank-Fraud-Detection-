import joblib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = "model"
print("Starting model load test...")

try:
    pkl_path = os.path.join(MODEL_DIR, "fraud_model.pkl")
    print(f"Loading model from {pkl_path}...")
    model = joblib.load(pkl_path)
    print("Model loaded successfully.")
    
    encoders_path = os.path.join(MODEL_DIR, "label_encoders.pkl")
    print(f"Loading encoders from {encoders_path}...")
    label_encoders = joblib.load(encoders_path)
    print("Encoders loaded successfully.")
    
    threshold_path = os.path.join(MODEL_DIR, "threshold.pkl")
    print(f"Loading threshold from {threshold_path}...")
    threshold = joblib.load(threshold_path)
    print(f"Threshold loaded successfully: {threshold}")
    
    print("ALL FILES LOADED SUCCESSFULLY!")
except Exception as e:
    print(f"ERROR: {e}")
