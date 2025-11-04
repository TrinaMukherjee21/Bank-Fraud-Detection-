"""
Enhanced Fraud Detection Model Training System
Professional-grade training pipeline with advanced features
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
import logging
from datetime import datetime
from typing import Dict, Tuple, Any, List
import warnings
warnings.filterwarnings('ignore')

# Machine Learning imports
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_val_score, 
    GridSearchCV, RandomizedSearchCV
)
from sklearn.preprocessing import LabelEncoder, StandardScaler, RobustScaler
from sklearn.metrics import (
    classification_report, f1_score, precision_score, recall_score,
    roc_auc_score, precision_recall_curve, roc_curve, confusion_matrix
)
from sklearn.ensemble import IsolationForest
from sklearn.feature_selection import SelectKBest, f_classif

# Advanced ML models
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier

# Imbalanced learning
from imblearn.combine import SMOTEENN, SMOTETomek
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.under_sampling import EditedNearestNeighbours

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
# Note: plot_confusion_matrix, plot_roc_curve, plot_precision_recall_curve are deprecated
# Using matplotlib directly for plotting

# Set up professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FraudDetectionTrainer:
    """
    Professional fraud detection model trainer with advanced features
    """
    
    def __init__(self, config_path: str = None):
        """Initialize the trainer with configuration"""
        self.config = self._load_config(config_path)
        self.models = {}
        self.encoders = {}
        self.scalers = {}
        self.feature_importance = {}
        self.training_history = {}
        self.best_model = None
        self.best_threshold = 0.5
        
        logger.info("FraudDetectionTrainer initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load training configuration"""
        default_config = {
            'data_path': 'Data/bs140513_032310.csv',
            'test_size': 0.2,
            'random_state': 42,
            'cv_folds': 5,
            'threshold_range': (0.3, 0.8, 0.05),
            'feature_selection': True,
            'hyperparameter_tuning': True,
            'ensemble_models': True,
            'save_plots': True,
            'model_versioning': True
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def load_and_explore_data(self) -> pd.DataFrame:
        """Load and perform exploratory data analysis"""
        logger.info(f"Loading data from {self.config['data_path']}")
        
        try:
            df = pd.read_csv(self.config['data_path'])
            logger.info(f"Data loaded successfully. Shape: {df.shape}")
            
            # Basic data exploration
            logger.info(f"Columns: {list(df.columns)}")
            logger.info(f"Missing values: {df.isnull().sum().sum()}")
            
            if 'fraud' in df.columns:
                fraud_rate = df['fraud'].mean()
                logger.info(f"Fraud rate: {fraud_rate:.4f} ({fraud_rate*100:.2f}%)")
                logger.info(f"Fraud cases: {df['fraud'].sum()}")
                logger.info(f"Legitimate cases: {(df['fraud'] == 0).sum()}")
            
            # Data quality checks
            self._perform_data_quality_checks(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise
    
    def _perform_data_quality_checks(self, df: pd.DataFrame):
        """Perform comprehensive data quality checks"""
        logger.info("Performing data quality checks...")
        
        # Check for duplicates
        duplicates = df.duplicated().sum()
        logger.info(f"Duplicate rows: {duplicates}")
        
        # Check data types
        logger.info("Data types:")
        for col, dtype in df.dtypes.items():
            logger.info(f"  {col}: {dtype}")
        
        # Check for outliers in numerical columns
        numerical_cols = df.select_dtypes(include=[np.number]).columns
        for col in numerical_cols:
            if col != 'fraud':
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                outliers = df[(df[col] < q1 - 1.5*iqr) | (df[col] > q3 + 1.5*iqr)].shape[0]
                logger.info(f"Outliers in {col}: {outliers} ({outliers/len(df)*100:.2f}%)")
    
    def advanced_preprocessing(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Advanced preprocessing with feature engineering"""
        logger.info("Starting advanced preprocessing...")
        
        # Create a copy for processing
        df_processed = df.copy()
        preprocessing_log = {}
        
        # 1. Handle missing values
        missing_before = df_processed.isnull().sum().sum()
        df_processed = df_processed.dropna()
        missing_after = df_processed.isnull().sum().sum()
        preprocessing_log['missing_handled'] = missing_before - missing_after
        
        # 2. Remove uninformative columns
        cols_to_drop = ["zipcodeOri", "zipMerchant", "merchant"]
        existing_cols_to_drop = [col for col in cols_to_drop if col in df_processed.columns]
        if existing_cols_to_drop:
            df_processed.drop(columns=existing_cols_to_drop, inplace=True)
            preprocessing_log['columns_dropped'] = existing_cols_to_drop
        
        # 3. Data validation and cleaning
        original_shape = df_processed.shape[0]
        df_processed = df_processed[df_processed['amount'] > 0]  # Remove zero/negative amounts
        df_processed = df_processed[df_processed['step'] > 0]    # Remove invalid steps
        preprocessing_log['invalid_records_removed'] = original_shape - df_processed.shape[0]
        
        # 4. Advanced feature engineering
        df_processed = self._engineer_features(df_processed)
        
        # 5. Encode categorical features
        categorical_cols = ["customer", "age", "gender", "category"]
        for col in categorical_cols:
            if col in df_processed.columns:
                le = LabelEncoder()
                df_processed[col] = df_processed[col].astype(str).fillna('unknown')
                df_processed[col] = le.fit_transform(df_processed[col])
                self.encoders[col] = le
                logger.info(f"Encoded {col}: {len(le.classes_)} unique values")
        
        # 6. Detect and handle outliers
        df_processed = self._handle_outliers(df_processed)
        
        preprocessing_log['final_shape'] = df_processed.shape
        logger.info(f"Preprocessing complete. Final shape: {df_processed.shape}")
        
        return df_processed, preprocessing_log
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Advanced feature engineering"""
        logger.info("Engineering advanced features...")
        
        # 1. Amount-based features
        df['log_amount'] = np.log1p(df['amount'])
        df['sqrt_amount'] = np.sqrt(df['amount'])
        df['amount_squared'] = df['amount'] ** 2
        
        # 2. Transaction size categories
        amount_percentiles = df['amount'].quantile([0.25, 0.5, 0.75, 0.95])
        df['is_small_transaction'] = (df['amount'] <= amount_percentiles[0.25]).astype(int)
        df['is_medium_transaction'] = ((df['amount'] > amount_percentiles[0.25]) & 
                                      (df['amount'] <= amount_percentiles[0.75])).astype(int)
        df['is_large_transaction'] = (df['amount'] > amount_percentiles[0.75]).astype(int)
        df['is_very_large_transaction'] = (df['amount'] > amount_percentiles[0.95]).astype(int)
        
        # 3. Time-based features
        df['step_log'] = np.log1p(df['step'])
        df['is_early_step'] = (df['step'] <= df['step'].quantile(0.25)).astype(int)
        df['is_late_step'] = (df['step'] >= df['step'].quantile(0.75)).astype(int)
        
        # 4. Customer behavior features (if customer data available)
        if 'customer' in df.columns:
            customer_stats = df.groupby('customer')['amount'].agg(['count', 'mean', 'std', 'sum'])
            customer_stats.columns = ['customer_transaction_count', 'customer_avg_amount', 
                                    'customer_amount_std', 'customer_total_amount']
            customer_stats = customer_stats.fillna(0)
            df = df.merge(customer_stats, left_on='customer', right_index=True, how='left')
        
        # 5. Category-based features
        if 'category' in df.columns:
            category_stats = df.groupby('category')['amount'].agg(['mean', 'std'])
            category_stats.columns = ['category_avg_amount', 'category_amount_std']
            category_stats = category_stats.fillna(0)
            df = df.merge(category_stats, left_on='category', right_index=True, how='left')
        
        # 6. Interaction features
        if all(col in df.columns for col in ['amount', 'step']):
            df['amount_per_step'] = df['amount'] / (df['step'] + 1)
        
        logger.info(f"Feature engineering complete. New shape: {df.shape}")
        return df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle outliers using various techniques"""
        logger.info("Handling outliers...")
        
        # Use Isolation Forest to detect anomalies
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if 'fraud' in numerical_cols:
            numerical_cols.remove('fraud')
        
        if len(numerical_cols) > 0:
            iso_forest = IsolationForest(contamination=0.1, random_state=self.config['random_state'])
            outlier_labels = iso_forest.fit_predict(df[numerical_cols])
            
            outlier_count = (outlier_labels == -1).sum()
            logger.info(f"Detected {outlier_count} outliers ({outlier_count/len(df)*100:.2f}%)")
            
            # For now, we'll keep outliers but flag them
            df['is_outlier'] = (outlier_labels == -1).astype(int)
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare features for training"""
        logger.info("Preparing features for training...")
        
        # Separate features and target
        if 'fraud' not in df.columns:
            raise ValueError("Target column 'fraud' not found in dataset")
        
        feature_columns = [col for col in df.columns if col != 'fraud']
        X = df[feature_columns]
        y = df['fraud']
        
        # Feature selection if enabled
        if self.config.get('feature_selection', False):
            X, feature_columns = self._select_features(X, y, feature_columns)
        
        # Feature scaling
        scaler = RobustScaler()  # More robust to outliers than StandardScaler
        X_scaled = scaler.fit_transform(X)
        self.scalers['features'] = scaler
        
        logger.info(f"Features prepared. Shape: {X_scaled.shape}")
        logger.info(f"Feature columns: {feature_columns}")
        
        return X_scaled, y.values, feature_columns
    
    def _select_features(self, X: pd.DataFrame, y: pd.Series, 
                        feature_columns: List[str]) -> Tuple[pd.DataFrame, List[str]]:
        """Select best features using statistical tests"""
        logger.info("Performing feature selection...")
        
        # Use SelectKBest with f_classif
        k_best = min(20, X.shape[1])  # Select top 20 features or all if less
        selector = SelectKBest(score_func=f_classif, k=k_best)
        X_selected = selector.fit_transform(X, y)
        
        # Get selected feature names
        selected_indices = selector.get_support(indices=True)
        selected_features = [feature_columns[i] for i in selected_indices]
        
        logger.info(f"Selected {len(selected_features)} features: {selected_features}")
        
        return pd.DataFrame(X_selected, columns=selected_features), selected_features
    
    def train_models(self, X: np.ndarray, y: np.ndarray, 
                    feature_names: List[str]) -> Dict[str, Any]:
        """Train multiple models with hyperparameter tuning"""
        logger.info("Starting model training...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config['test_size'], 
            random_state=self.config['random_state'], stratify=y
        )
        
        # Handle class imbalance
        X_train_balanced, y_train_balanced = self._balance_dataset(X_train, y_train)
        
        # Define models to train
        models_to_train = {
            'XGBoost': self._get_xgboost_model(),
            'LightGBM': self._get_lightgbm_model(),
            'RandomForest': self._get_random_forest_model()
        }
        
        # Add CatBoost if available
        try:
            models_to_train['CatBoost'] = self._get_catboost_model()
        except:
            logger.warning("CatBoost not available, skipping...")
        
        # Train each model
        model_results = {}
        for name, model in models_to_train.items():
            logger.info(f"Training {name}...")
            
            try:
                # Hyperparameter tuning if enabled
                if self.config.get('hyperparameter_tuning', False):
                    model = self._tune_hyperparameters(model, X_train_balanced, y_train_balanced)
                
                # Train model
                model.fit(X_train_balanced, y_train_balanced)
                
                # Evaluate model
                results = self._evaluate_model(model, X_test, y_test, name)
                results['model'] = model
                model_results[name] = results
                
                logger.info(f"{name} - F1 Score: {results['f1_score']:.4f}")
                
            except Exception as e:
                logger.error(f"Error training {name}: {str(e)}")
                continue
        
        # Select best model
        if model_results:
            best_model_name = max(model_results.keys(), 
                                key=lambda k: model_results[k]['f1_score'])
            self.best_model = model_results[best_model_name]['model']
            logger.info(f"Best model: {best_model_name}")
        
        # Train ensemble if enabled
        if self.config.get('ensemble_models', False) and len(model_results) > 1:
            ensemble_model = self._create_ensemble(model_results)
            if ensemble_model:
                ensemble_results = self._evaluate_model(ensemble_model, X_test, y_test, 'Ensemble')
                ensemble_results['model'] = ensemble_model
                model_results['Ensemble'] = ensemble_results
        
        # Find optimal threshold
        if self.best_model:
            self.best_threshold = self._find_optimal_threshold(
                self.best_model, X_test, y_test
            )
        
        # Store training data for later use
        self.training_history = {
            'X_test': X_test,
            'y_test': y_test,
            'feature_names': feature_names,
            'model_results': model_results
        }
        
        return model_results
    
    def _balance_dataset(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Balance dataset using advanced sampling techniques"""
        logger.info("Balancing dataset...")
        
        original_ratio = np.mean(y)
        logger.info(f"Original fraud ratio: {original_ratio:.4f}")
        
        # Use SMOTE-ENN for balanced sampling
        smote_enn = SMOTEENN(random_state=self.config['random_state'])
        X_balanced, y_balanced = smote_enn.fit_resample(X, y)
        
        new_ratio = np.mean(y_balanced)
        logger.info(f"Balanced fraud ratio: {new_ratio:.4f}")
        logger.info(f"Balanced dataset shape: {X_balanced.shape}")
        
        return X_balanced, y_balanced
    
    def _get_xgboost_model(self) -> XGBClassifier:
        """Get XGBoost model with optimized parameters"""
        return XGBClassifier(
            max_depth=6,
            learning_rate=0.1,
            n_estimators=300,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric='logloss',
            random_state=self.config['random_state'],
            n_jobs=-1
        )
    
    def _get_lightgbm_model(self) -> LGBMClassifier:
        """Get LightGBM model with optimized parameters"""
        return LGBMClassifier(
            max_depth=6,
            learning_rate=0.1,
            n_estimators=300,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=self.config['random_state'],
            n_jobs=-1,
            verbose=-1
        )
    
    def _get_random_forest_model(self) -> RandomForestClassifier:
        """Get Random Forest model with optimized parameters"""
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=self.config['random_state'],
            n_jobs=-1
        )
    
    def _get_catboost_model(self) -> CatBoostClassifier:
        """Get CatBoost model with optimized parameters"""
        return CatBoostClassifier(
            iterations=300,
            depth=6,
            learning_rate=0.1,
            random_seed=self.config['random_state'],
            verbose=False
        )
    
    def _tune_hyperparameters(self, model, X: np.ndarray, y: np.ndarray):
        """Tune hyperparameters using RandomizedSearchCV"""
        logger.info("Tuning hyperparameters...")
        
        # Define parameter grids for different models
        param_grids = {
            'XGBClassifier': {
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2],
                'n_estimators': [100, 200, 300],
                'subsample': [0.8, 0.9, 1.0],
                'colsample_bytree': [0.8, 0.9, 1.0]
            },
            'LGBMClassifier': {
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2],
                'n_estimators': [100, 200, 300],
                'subsample': [0.8, 0.9, 1.0],
                'colsample_bytree': [0.8, 0.9, 1.0]
            },
            'RandomForestClassifier': {
                'n_estimators': [100, 200, 300],
                'max_depth': [5, 10, 15, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        }
        
        model_name = type(model).__name__
        if model_name in param_grids:
            param_grid = param_grids[model_name]
            
            # Use RandomizedSearchCV for efficiency
            search = RandomizedSearchCV(
                model, param_grid, n_iter=20, cv=3,
                scoring='f1', random_state=self.config['random_state'],
                n_jobs=-1, verbose=0
            )
            
            search.fit(X, y)
            logger.info(f"Best parameters for {model_name}: {search.best_params_}")
            return search.best_estimator_
        
        return model
    
    def _evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray, 
                       model_name: str) -> Dict[str, float]:
        """Comprehensive model evaluation"""
        # Make predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        results = {
            'accuracy': (y_pred == y_test).mean(),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba)
        }
        
        # Cross-validation score
        cv_scores = cross_val_score(
            model, X_test, y_test, cv=5, scoring='f1'
        )
        results['cv_f1_mean'] = cv_scores.mean()
        results['cv_f1_std'] = cv_scores.std()
        
        return results
    
    def _find_optimal_threshold(self, model, X_test: np.ndarray, 
                               y_test: np.ndarray) -> float:
        """Find optimal threshold for binary classification"""
        logger.info("Finding optimal threshold...")
        
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        best_f1 = 0
        best_threshold = 0.5
        
        threshold_config = self.config['threshold_range']
        if isinstance(threshold_config, list) and len(threshold_config) == 3:
            start, end, step = threshold_config
        elif isinstance(threshold_config, tuple) and len(threshold_config) == 3:
            start, end, step = threshold_config
        else:
            # Default fallback
            start, end, step = 0.3, 0.8, 0.05
        
        for threshold in np.arange(start, end, step):
            y_pred_thresh = (y_pred_proba >= threshold).astype(int)
            f1 = f1_score(y_test, y_pred_thresh)
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
        
        logger.info(f"Optimal threshold: {best_threshold:.2f} (F1: {best_f1:.4f})")
        return best_threshold
    
    def _create_ensemble(self, model_results: Dict[str, Any]) -> VotingClassifier:
        """Create ensemble model from trained models"""
        logger.info("Creating ensemble model...")
        
        try:
            # Select top 3 models based on F1 score
            sorted_models = sorted(
                model_results.items(), 
                key=lambda x: x[1]['f1_score'], 
                reverse=True
            )[:3]
            
            estimators = [(name, results['model']) for name, results in sorted_models]
            
            ensemble = VotingClassifier(
                estimators=estimators, 
                voting='soft'
            )
            
            return ensemble
            
        except Exception as e:
            logger.error(f"Error creating ensemble: {str(e)}")
            return None
    
    def save_model(self, model_dir: str = "model") -> Dict[str, str]:
        """Save trained models and artifacts"""
        logger.info("Saving models and artifacts...")
        
        os.makedirs(model_dir, exist_ok=True)
        saved_files = {}
        
        try:
            # Save best model
            if self.best_model:
                model_path = os.path.join(model_dir, "fraud_model.pkl")
                joblib.dump(self.best_model, model_path)
                saved_files['model'] = model_path
            
            # Save encoders
            if self.encoders:
                encoders_path = os.path.join(model_dir, "label_encoders.pkl")
                joblib.dump(self.encoders, encoders_path)
                saved_files['encoders'] = encoders_path
            
            # Save scalers
            if self.scalers:
                scalers_path = os.path.join(model_dir, "scalers.pkl")
                joblib.dump(self.scalers, scalers_path)
                saved_files['scalers'] = scalers_path
            
            # Save threshold
            threshold_path = os.path.join(model_dir, "threshold.pkl")
            joblib.dump(self.best_threshold, threshold_path)
            saved_files['threshold'] = threshold_path
            
            # Save training metadata
            metadata = {
                'training_date': datetime.now().isoformat(),
                'config': self.config,
                'feature_names': self.training_history.get('feature_names', []),
                'model_performance': {
                    name: {k: v for k, v in results.items() if k != 'model'}
                    for name, results in self.training_history.get('model_results', {}).items()
                },
                'best_threshold': self.best_threshold
            }
            
            metadata_path = os.path.join(model_dir, "training_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            saved_files['metadata'] = metadata_path
            
            logger.info(f"Models saved successfully to {model_dir}")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
            raise
        
        return saved_files
    
    def generate_training_report(self, output_path: str = "training_report.html"):
        """Generate comprehensive training report"""
        logger.info("Generating training report...")
        
        if not self.training_history:
            logger.warning("No training history available for report generation")
            return
        
        try:
            # Create visualizations
            self._create_training_plots()
            
            # Generate HTML report
            html_content = self._generate_html_report()
            
            with open(output_path, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Training report saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
    
    def _create_training_plots(self):
        """Create training visualization plots"""
        if not self.config.get('save_plots', False):
            return
        
        # Create plots directory
        os.makedirs('plots', exist_ok=True)
        
        # Model comparison plot
        model_results = self.training_history.get('model_results', {})
        if model_results:
            models = list(model_results.keys())
            f1_scores = [results['f1_score'] for results in model_results.values()]
            
            plt.figure(figsize=(10, 6))
            plt.bar(models, f1_scores)
            plt.title('Model Performance Comparison (F1 Score)')
            plt.ylabel('F1 Score')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig('plots/model_comparison.png')
            plt.close()
    
    def _generate_html_report(self) -> str:
        """Generate HTML training report"""
        # This would generate a comprehensive HTML report
        # For brevity, returning a simple template
        model_name = type(self.best_model).__name__ if self.best_model else 'None'
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
        <html>
        <head><title>Fraud Detection Model Training Report</title></head>
        <body>
        <h1>Fraud Detection Model Training Report</h1>
        <h2>Training Summary</h2>
        <p>Training completed on: {current_time}</p>
        <p>Best Model: {model_name}</p>
        <p>Optimal Threshold: {self.best_threshold:.3f}</p>
        
        <h2>Model Performance</h2>
        <!-- Model performance details would go here -->
        
        </body>
        </html>
        """

def main():
    """Main training pipeline"""
    # Initialize trainer
    trainer = FraudDetectionTrainer()
    
    # Load and explore data
    df = trainer.load_and_explore_data()
    
    # Advanced preprocessing
    df_processed, preprocessing_log = trainer.advanced_preprocessing(df)
    
    # Prepare features
    X, y, feature_names = trainer.prepare_features(df_processed)
    
    # Train models
    model_results = trainer.train_models(X, y, feature_names)
    
    # Save models
    saved_files = trainer.save_model()
    
    # Generate report
    trainer.generate_training_report()
    
    logger.info("Training pipeline completed successfully!")
    logger.info(f"Saved files: {saved_files}")

if __name__ == "__main__":
    main()