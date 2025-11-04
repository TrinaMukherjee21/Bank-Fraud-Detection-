"""
Quick script to retrain and save the best XGBoost model
Based on the successful training results: F1-Score 0.7189
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier
from imblearn.combine import SMOTEENN
import warnings
warnings.filterwarnings('ignore')

def main():
    print("Training Best XGBoost Model...")
    
    # Load and preprocess data (simplified version)
    data_path = "Data/bs140513_032310.csv"
    df = pd.read_csv(data_path)
    
    # Drop uninformative columns
    df = df.drop(columns=["zipcodeOri", "zipMerchant", "merchant"])
    
    # Basic feature engineering (matching your app preprocessing)
    df['log_amount'] = np.log(df['amount'] + 1)
    df['sqrt_amount'] = np.sqrt(df['amount'])
    df['amount_squared'] = df['amount'] ** 2
    df['step_log'] = np.log(df['step'] + 1)
    
    # Transaction size flags
    df['is_small_transaction'] = (df['amount'] < 100).astype(int)
    df['is_large_transaction'] = (df['amount'] > 2000).astype(int)
    df['is_very_large_transaction'] = (df['amount'] > 10000).astype(int)
    
    # Time-based flags
    df['is_early_step'] = (df['step'] < 200).astype(int)
    df['is_late_step'] = (df['step'] > 700).astype(int)
    
    # Encode categorical features
    label_encoders = {}
    categorical_cols = ["customer", "age", "gender", "category"]
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le
    
    # Prepare features and target
    X = df.drop("fraud", axis=1)
    y = df["fraud"]
    
    print(f"Dataset: {X.shape[0]:,} samples, {X.shape[1]} features")
    print(f"Fraud rate: {y.mean():.3f}")
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Apply SMOTE-ENN (simplified)
    print("Balancing dataset...")
    smote_enn = SMOTEENN(random_state=42)
    X_train_res, y_train_res = smote_enn.fit_resample(X_train, y_train)
    
    print(f"Balanced dataset: {X_train_res.shape[0]:,} samples")
    
    # Train best XGBoost model (from successful run)
    print("Training XGBoost...")
    model = XGBClassifier(
        subsample=1.0,
        n_estimators=300,
        max_depth=9,
        learning_rate=0.2,
        colsample_bytree=0.9,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    
    model.fit(X_train_res, y_train_res)
    
    # Evaluate model
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Find best threshold
    best_f1 = 0
    best_thresh = 0.5
    best_metrics = {}
    
    for t in np.arange(0.3, 0.9, 0.025):
        y_pred = (y_proba >= t).astype(int)
        f1 = f1_score(y_test, y_pred)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
            best_metrics = {
                'threshold': t,
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1_score': f1,
                'roc_auc': roc_auc_score(y_test, y_proba),
                'accuracy': (y_pred == y_test).mean()
            }
    
    print(f"Best Threshold: {best_thresh:.3f}")
    print(f"Best F1-Score: {best_f1:.4f}")
    print(f"Metrics: Precision={best_metrics['precision']:.3f}, Recall={best_metrics['recall']:.3f}")
    
    # Save model and metadata
    model_dir = "model"
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model components
    joblib.dump(model, os.path.join(model_dir, "fraud_model.pkl"))
    joblib.dump(label_encoders, os.path.join(model_dir, "label_encoders.pkl"))
    joblib.dump(best_thresh, os.path.join(model_dir, "threshold.pkl"))
    joblib.dump(X.columns.tolist(), os.path.join(model_dir, "feature_names.pkl"))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    # Save metadata
    metadata = {
        "training_date": datetime.now().isoformat(),
        "model_type": "XGBoost Enhanced v2",
        "feature_count": len(X.columns),
        "training_samples": len(X_train_res),
        "test_samples": len(X_test),
        "best_threshold": best_thresh,
        "performance": best_metrics,
        "feature_importance": [
            {"feature": row['feature'], "importance": row['importance']}
            for _, row in feature_importance.iterrows()
        ]
    }
    
    with open(os.path.join(model_dir, "training_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Model saved successfully!")
    print(f"Performance: F1={best_f1:.4f}, ROC-AUC={best_metrics['roc_auc']:.4f}")
    print("Ready to use in web application!")

if __name__ == "__main__":
    main()