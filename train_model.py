"""
Simplified Model Training Script
Run this to train your fraud detection model with enhanced features
"""

import sys
import os
import pandas as pd
import numpy as np
import joblib
import logging
from datetime import datetime

# ML imports
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from xgboost import XGBClassifier
from imblearn.combine import SMOTEENN

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_fraud_model():
    """Train the fraud detection model"""
    
    print("Starting Enhanced Fraud Detection Model Training...")
    print("=" * 60)
    
    # 1. Load Data
    print("Loading data...")
    try:
        data_path = "Data/bs140513_032310.csv"
        df = pd.read_csv(data_path)
        print(f"Data loaded successfully. Shape: {df.shape}")
        print(f"Fraud rate: {df['fraud'].mean():.4f} ({df['fraud'].sum()} fraudulent transactions)")
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
    
    # 2. Data Preprocessing
    print("\nPreprocessing data...")
    
    # Drop uninformative columns
    if 'zipcodeOri' in df.columns:
        df = df.drop(columns=["zipcodeOri", "zipMerchant", "merchant"])
    
    # Clean data
    original_shape = df.shape[0]
    df = df.dropna()
    df = df[df['amount'] > 0]
    df = df[df['step'] > 0]
    print(f"Data cleaned. Removed {original_shape - df.shape[0]} invalid records")
    
    # 3. Enhanced Feature Engineering (must match preprocessing pipeline exactly)
    print("\nCreating advanced features to match preprocessing pipeline...")
    
    # Amount-based features (exact match with preprocess.py)
    df['log_amount'] = np.log(df['amount'] + 1)  # Use np.log, not np.log1p for consistency
    df['sqrt_amount'] = np.sqrt(df['amount'])
    df['amount_squared'] = df['amount'] ** 2
    
    # Time-based features
    df['step_log'] = np.log(df['step'] + 1)  # Use np.log, not np.log1p for consistency
    
    # Transaction size flags (exact thresholds from preprocessing)
    df['is_small_transaction'] = (df['amount'] < 100).astype(int)
    df['is_large_transaction'] = (df['amount'] > 2000).astype(int)
    df['is_very_large_transaction'] = (df['amount'] > 10000).astype(int)
    
    # Time-based flags (exact thresholds from preprocessing)
    df['is_early_step'] = (df['step'] < 200).astype(int)
    df['is_late_step'] = (df['step'] > 700).astype(int)
    
    print(f"Created {df.shape[1] - original_shape + (original_shape - df.shape[0])} new features")
    
    # 4. Encode Categorical Features
    print("\nEncoding categorical features...")
    label_encoders = {}
    categorical_cols = ["customer", "age", "gender", "category"]
    
    for col in categorical_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = df[col].astype(str).fillna('unknown')
            df[col] = le.fit_transform(df[col])
            label_encoders[col] = le
            print(f"   {col}: {len(le.classes_)} unique values")
    
    # 5. Prepare Features and Target (exact order from preprocessing pipeline)
    print("\nPreparing features and target...")
    
    # Define feature columns in exact order expected by preprocessing pipeline
    feature_columns = [
        'step', 'customer', 'age', 'gender', 'category', 'amount',
        'log_amount', 'sqrt_amount', 'amount_squared', 'step_log',
        'is_small_transaction', 'is_large_transaction', 'is_very_large_transaction',
        'is_early_step', 'is_late_step'
    ]
    
    # Verify all features exist
    missing_features = [col for col in feature_columns if col not in df.columns]
    if missing_features:
        print(f"Missing required features: {missing_features}")
        return False
    
    X = df[feature_columns]  # Select features in exact order
    y = df['fraud']
    
    print(f"Features: {X.shape[1]} columns (15 features as required)")
    print(f"Samples: {X.shape[0]} rows")
    print(f"Feature order: {feature_columns}")
    
    # 6. Train-Test Split
    print("\nSplitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    # 7. Handle Class Imbalance
    print("\nBalancing dataset...")
    print(f"Original fraud ratio: {y_train.mean():.4f}")
    
    smote_enn = SMOTEENN(random_state=42)
    X_train_balanced, y_train_balanced = smote_enn.fit_resample(X_train, y_train)
    
    print(f"Balanced fraud ratio: {y_train_balanced.mean():.4f}")
    print(f"Balanced dataset size: {X_train_balanced.shape[0]} samples")
    
    # 8. Train Enhanced XGBoost Model
    print("\nTraining XGBoost model...")
    
    model = XGBClassifier(
        # Enhanced parameters for better performance
        max_depth=8,
        learning_rate=0.05,
        n_estimators=500,
        subsample=0.8,
        colsample_bytree=0.8,
        colsample_bylevel=0.8,
        gamma=0.1,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=1,  # Will be handled by balanced data
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=50
    )
    
    # Train with validation set for early stopping
    eval_set = [(X_test, y_test)]
    
    model.fit(
        X_train_balanced, y_train_balanced,
        eval_set=eval_set,
        verbose=False
    )
    
    print("Model training completed!")
    
    # 9. Find Optimal Threshold
    print("\nFinding optimal threshold...")
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    best_f1 = 0
    best_threshold = 0.5
    
    print("Threshold | F1-Score | Precision | Recall")
    print("-" * 40)
    
    for threshold in np.arange(0.3, 0.8, 0.05):
        y_pred_thresh = (y_pred_proba >= threshold).astype(int)
        f1 = f1_score(y_test, y_pred_thresh)
        
        # Calculate precision and recall for display
        from sklearn.metrics import precision_score, recall_score
        precision = precision_score(y_test, y_pred_thresh)
        recall = recall_score(y_test, y_pred_thresh)
        
        print(f"  {threshold:.2f}    |  {f1:.4f}  |   {precision:.4f}  |  {recall:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    print(f"\nBest threshold: {best_threshold:.2f} (F1-Score: {best_f1:.4f})")
    
    # 10. Final Model Evaluation
    print("\nFinal model evaluation...")
    y_pred_final = (y_pred_proba >= best_threshold).astype(int)
    
    # Comprehensive metrics
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    
    accuracy = accuracy_score(y_test, y_pred_final)
    precision = precision_score(y_test, y_pred_final)
    recall = recall_score(y_test, y_pred_final)
    f1 = f1_score(y_test, y_pred_final)
    auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"Final Model Performance:")
    print(f"   Accuracy:  {accuracy:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   ROC AUC:   {auc:.4f}")
    
    # Feature importance
    print("\nTop 10 Most Important Features:")
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
        print(f"   {i+1:2d}. {row['feature']:<20} ({row['importance']:.4f})")
    
    # 11. Save Model and Artifacts
    print("\nSaving model and artifacts...")
    
    model_dir = "model"
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model
    model_path = os.path.join(model_dir, "fraud_model.pkl")
    joblib.dump(model, model_path)
    
    # Save encoders
    encoders_path = os.path.join(model_dir, "label_encoders.pkl")
    joblib.dump(label_encoders, encoders_path)
    
    # Save threshold
    threshold_path = os.path.join(model_dir, "threshold.pkl")
    joblib.dump(best_threshold, threshold_path)
    
    # Save feature names
    features_path = os.path.join(model_dir, "feature_names.pkl")
    joblib.dump(feature_columns, features_path)
    
    # Save training metadata
    metadata = {
        'training_date': datetime.now().isoformat(),
        'model_type': 'XGBoost Enhanced',
        'feature_count': len(feature_columns),
        'training_samples': X_train_balanced.shape[0],
        'test_samples': X_test.shape[0],
        'best_threshold': best_threshold,
        'performance': {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'roc_auc': auc
        },
        'feature_importance': feature_importance.to_dict('records')
    }
    
    metadata_path = os.path.join(model_dir, "training_metadata.json")
    import json
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Model saved to: {model_path}")
    print(f"Encoders saved to: {encoders_path}")
    print(f"Threshold saved to: {threshold_path}")
    print(f"Metadata saved to: {metadata_path}")
    
    print("\nTraining completed successfully!")
    print("=" * 60)
    print(f"Your enhanced fraud detection model is ready!")
    print(f"Achieved F1-Score: {f1:.4f}")
    print(f"Optimal Threshold: {best_threshold:.2f}")
    print("You can now use the Flask app to test predictions!")
    
    return True

if __name__ == "__main__":
    success = train_fraud_model()
    if success:
        print("\nRun 'python app.py' to start the fraud detection system!")
    else:
        print("\nTraining failed. Please check the error messages above.")
        sys.exit(1)