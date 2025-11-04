# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a bank fraud detection system built with Flask that uses machine learning to predict fraudulent transactions. The system provides both a basic and advanced form interface for users to input transaction details and receive fraud predictions.

## Architecture

### Core Components

- **Flask Web Application** (`app.py`): Main web server handling routes and predictions
- **Machine Learning Pipeline** (`train_model.ipynb`): XGBoost classifier with SMOTE-ENN for handling class imbalance
- **Preprocessing Module** (`utils/preprocess.py`): Data preprocessing and label encoding utilities
- **Pre-trained Models** (`model/`): Serialized model, label encoders, and optimal threshold

### Data Flow

1. **Training Pipeline**: Raw transaction data → preprocessing → feature engineering → SMOTE-ENN balancing → XGBoost training → model serialization
2. **Prediction Pipeline**: User input → feature preparation → model prediction → probability thresholding → result display

### Key Features

- **Two Input Forms**: Basic form (simplified) and advanced form (all features)
- **Feature Engineering**: Log transformation of amounts, binary flag for large transactions
- **Threshold Optimization**: Uses F1-score optimized threshold (0.75) instead of default 0.5
- **Categorical Encoding**: LabelEncoder for customer, age, gender, and category fields

## Development Commands

### Setup and Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python app.py
```
The Flask app runs in debug mode on http://localhost:5000

### Model Training
Open and run `train_model.ipynb` in Jupyter notebook to retrain the model with new data.

## Model Details

### Features Used
- `step`: Transaction sequence number
- `customer`: Customer ID (encoded)
- `age`: Customer age group (encoded)
- `gender`: Customer gender (encoded)
- `category`: Transaction category (encoded)
- `amount`: Transaction amount
- `log_amount`: Log-transformed amount
- `is_large_transaction`: Binary flag for amounts > 2000

### Model Performance
- **Algorithm**: XGBoost with class weight balancing
- **Preprocessing**: SMOTE-ENN for handling class imbalance
- **Optimal Threshold**: 0.75 (F1-score optimized)
- **Final F1-Score**: 0.54 on fraud class

### Prediction Logic
The Flask app handles two form types:
- **Basic Form**: Uses placeholders (0) for missing customer, age, and merchant_id
- **Advanced Form**: Uses all available features

## File Structure

```
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── train_model.ipynb        # Model training notebook
├── utils/
│   └── preprocess.py        # Data preprocessing utilities
├── model/                   # Serialized models and encoders
│   ├── fraud_model.pkl      # Trained XGBoost model
│   ├── label_encoders.pkl   # LabelEncoder objects
│   └── threshold.pkl        # Optimal prediction threshold
├── templates/               # HTML templates
│   ├── base.html           # Base template
│   ├── home.html           # Landing page
│   ├── form_basic.html     # Basic input form
│   ├── form_advanced.html  # Advanced input form
│   └── result.html         # Prediction results
├── static/css/             # Styling
└── Data/                   # Training datasets
```

## Important Notes

- The model expects specific categorical encodings - use existing label encoders for consistency
- Transaction amounts are processed with log transformation during feature engineering
- The system uses a custom threshold (0.75) for binary classification instead of default 0.5
- Error handling in the Flask app catches prediction failures and returns error messages
- HTML templates use Jinja2 templating with a base template pattern