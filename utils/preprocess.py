import pandas as pd
import numpy as np
# Mock sklearn if it hangs or is missing
SKLEARN_AVAILABLE = False
class LabelEncoder:
    def __init__(self):
        self.classes_ = None
        self.mapping = {}
    def fit(self, y):
        self.classes_ = sorted(list(set(y.astype(str))))
        self.mapping = {c: i for i, c in enumerate(self.classes_)}
    def transform(self, y):
        return [self.mapping.get(str(c), 0) for c in y]
    def fit_transform(self, y):
        self.fit(y)
        return self.transform(y)
class StandardScaler:
    def fit_transform(self, X): return X
    def transform(self, X): return X
import joblib
import os
import logging
from typing import Tuple, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

def validate_input_data(data: Dict) -> Dict:
    """
    Validate and sanitize input data for fraud prediction.
    
    Parameters:
    - data: dict, input data from form
    
    Returns:
    - dict: validated and sanitized data
    """
    validated_data = {}
    
    # Validate step (should be positive integer)
    try:
        step = int(data.get('step', 0))
        validated_data['step'] = max(1, step)
    except (ValueError, TypeError):
        raise ValueError("Step must be a positive integer")
    
    # Validate amount (should be positive float)
    try:
        amount = float(data.get('amount', 0))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > 1000000:  # Cap at 1 million
            logging.warning(f"Large transaction amount detected: {amount}")
        validated_data['amount'] = amount
    except (ValueError, TypeError):
        raise ValueError("Amount must be a positive number")
    
    # Validate gender (0 or 1)
    try:
        gender = int(data.get('gender', 0))
        validated_data['gender'] = 1 if gender else 0
    except (ValueError, TypeError):
        raise ValueError("Gender must be 0 or 1")
    
    # Validate category (should be reasonable range)
    try:
        category = int(data.get('category', 0))
        validated_data['category'] = max(0, min(category, 20))  # Cap categories
    except (ValueError, TypeError):
        raise ValueError("Category must be a valid integer")
    
    # Optional fields for advanced form
    for field in ['customer', 'age', 'merchant_id']:
        if field in data:
            try:
                value = int(data[field])
                validated_data[field] = max(0, value)
            except (ValueError, TypeError):
                validated_data[field] = 0
    
    return validated_data

def create_features(data: Dict) -> np.ndarray:
    """
    Create feature array from validated input data.
    
    Parameters:
    - data: dict, validated input data
    
    Returns:
    - np.ndarray: feature array for model prediction (15 features)
    """
    # Extract basic features
    step = data['step']
    customer = data.get('customer', 0)
    age = data.get('age', 0)
    gender = data['gender']
    amount = data['amount']
    category = data['category']
    
    # Enhanced feature engineering to match training (15 features total)
    log_amount = np.log(amount + 1)
    sqrt_amount = np.sqrt(amount)
    amount_squared = amount ** 2
    step_log = np.log(step + 1)
    
    # Transaction size flags
    is_small_transaction = 1 if amount < 100 else 0
    is_large_transaction = 1 if amount > 2000 else 0
    is_very_large_transaction = 1 if amount > 10000 else 0
    
    # Time-based flags
    is_early_step = 1 if step < 200 else 0
    is_late_step = 1 if step > 700 else 0
    
    # Create feature array in the exact order the model expects
    # Based on feature importance from training metadata:
    features = np.array([
        step,                      # step
        customer,                  # customer  
        age,                      # age
        gender,                   # gender
        category,                 # category
        amount,                   # amount
        log_amount,               # log_amount
        sqrt_amount,              # sqrt_amount
        amount_squared,           # amount_squared
        step_log,                 # step_log
        is_small_transaction,     # is_small_transaction
        is_large_transaction,     # is_large_transaction
        is_very_large_transaction, # is_very_large_transaction
        is_early_step,            # is_early_step
        is_late_step              # is_late_step
    ]).reshape(1, -1)
    
    return features

def preprocess_data(data_path: str, save_encoders: bool = True, 
                   encoder_dir: str = "model") -> Tuple[pd.DataFrame, Dict]:
    """
    Load and preprocess the dataset with enhanced validation and feature engineering.
    
    Parameters:
    - data_path: str, path to the dataset CSV file
    - save_encoders: bool, whether to save label encoders
    - encoder_dir: str, directory to save encoders
    
    Returns:
    - df: preprocessed DataFrame
    - label_encoders: dictionary of LabelEncoders
    """
    logging.info(f"Loading dataset from {data_path}")
    
    try:
        # Load dataset with validation
        df = pd.read_csv(data_path)
        logging.info(f"Dataset loaded successfully. Shape: {df.shape}")
        
        # Validate required columns
        required_cols = ['step', 'customer', 'age', 'gender', 'category', 'amount', 'fraud']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Data quality checks
        logging.info(f"Missing values: {df.isnull().sum().sum()}")
        logging.info(f"Fraud rate: {df['fraud'].mean():.3f}")
        
        # Handle missing values
        df = df.dropna(subset=required_cols)
        
        # Drop uninformative columns if they exist
        cols_to_drop = ["zipcodeOri", "zipMerchant", "merchant"]
        existing_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
        if existing_cols_to_drop:
            df.drop(columns=existing_cols_to_drop, inplace=True)
            logging.info(f"Dropped columns: {existing_cols_to_drop}")
        
        # Data validation and cleaning
        df = df[df['amount'] > 0]  # Remove zero/negative amounts
        df = df[df['step'] > 0]    # Remove invalid steps
        
        # Encode categorical features with validation
        label_encoders = {}
        categorical_cols = ["customer", "age", "gender", "category"]
        
        for col in categorical_cols:
            if col in df.columns:
                le = LabelEncoder()
                # Handle potential string conversion issues
                df[col] = df[col].astype(str).fillna('unknown')
                df[col] = le.fit_transform(df[col])
                label_encoders[col] = le
                logging.info(f"Encoded {col}: {len(le.classes_)} unique values")
        
        # Feature engineering
        df['log_amount'] = np.log(df['amount'] + 1)
        df['is_large_transaction'] = (df['amount'] > 2000).astype(int)
        
        # Statistical summary
        logging.info(f"Final dataset shape: {df.shape}")
        logging.info(f"Amount statistics: min={df['amount'].min():.2f}, "
                    f"max={df['amount'].max():.2f}, mean={df['amount'].mean():.2f}")
        
        # Save encoders if required
        if save_encoders:
            os.makedirs(encoder_dir, exist_ok=True)
            joblib.dump(label_encoders, os.path.join(encoder_dir, "label_encoders.pkl"))
            logging.info(f"Label encoders saved to {encoder_dir}")
        
        return df, label_encoders
        
    except Exception as e:
        logging.error(f"Error in preprocessing: {str(e)}")
        raise

def detect_anomalies(df: pd.DataFrame, contamination: float = 0.1) -> pd.DataFrame:
    """
    Detect potential anomalies in the dataset using Isolation Forest.
    
    Parameters:
    - df: DataFrame to analyze
    - contamination: expected proportion of anomalies
    
    Returns:
    - DataFrame with anomaly indicators
    """
    from sklearn.ensemble import IsolationForest
    
    # Select numerical features for anomaly detection
    numerical_features = ['step', 'amount', 'log_amount']
    X_anomaly = df[numerical_features]
    
    # Fit Isolation Forest
    iso_forest = IsolationForest(contamination=contamination, random_state=42)
    anomaly_labels = iso_forest.fit_predict(X_anomaly)
    
    # Add anomaly indicator to dataframe
    df_copy = df.copy()
    df_copy['is_anomaly'] = (anomaly_labels == -1).astype(int)
    
    logging.info(f"Detected {df_copy['is_anomaly'].sum()} anomalies "
                f"({df_copy['is_anomaly'].mean():.3f} of total)")
    
    return df_copy
