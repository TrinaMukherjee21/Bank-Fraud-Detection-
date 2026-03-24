import sys
print("Starting import check...")
try:
    print("Importing flask...")
    from flask import Flask
    print("Importing flask_login...")
    from flask_login import LoginManager
    print("Importing joblib...")
    import joblib
    print("Importing numpy...")
    import numpy as np
    print("Importing xgboost...")
    import xgboost
    print("Importing pandas...")
    import pandas as pd
    print("Importing utils.preprocess...")
    from utils.preprocess import validate_input_data
    print("Import check complete!")
except Exception as e:
    print(f"Error during import: {e}")
except ImportError as e:
    print(f"ImportError: {e}")
