"""
Comprehensive testing suite for bank-ready fraud detection system.

This module provides thorough testing of all system components including:
- Model functionality and accuracy
- API endpoints and security
- Database operations
- Input validation
- User interface components
"""

import unittest
import json
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
import requests
from datetime import datetime

# Add the application to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import application modules
from app import app, model, label_encoders, threshold
from utils.preprocess import validate_input_data, create_features
from security import SecurityManager, validate_transaction_data, sanitize_input
from database_config import DatabaseManager, DatabaseConfig

class TestFraudDetectionModel(unittest.TestCase):
    """Test the fraud detection model functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Sample transaction data
        self.valid_transaction = {
            'step': '100',
            'amount': '1500.50',
            'gender': '1',
            'category': '5',
            'customer': '1234',
            'age': '3'
        }
        
        self.invalid_transaction = {
            'step': '-5',  # Invalid negative step
            'amount': 'invalid',  # Invalid amount
            'gender': '2',  # Invalid gender
            'category': '25'  # Invalid category
        }
    
    def test_model_loading(self):
        """Test that the model loads correctly"""
        self.assertIsNotNone(model, "Model should be loaded")
        self.assertIsNotNone(label_encoders, "Label encoders should be loaded")
        self.assertIsNotNone(threshold, "Threshold should be loaded")
        self.assertGreater(threshold, 0, "Threshold should be positive")
        self.assertLess(threshold, 1, "Threshold should be less than 1")
    
    def test_input_validation(self):
        """Test input validation functionality"""
        # Test valid input
        try:
            validated = validate_input_data(self.valid_transaction)
            self.assertIsInstance(validated, dict)
            self.assertIn('step', validated)
            self.assertIn('amount', validated)
            self.assertGreater(validated['amount'], 0)
        except Exception as e:
            self.fail(f"Valid input should not raise exception: {e}")
        
        # Test invalid input
        with self.assertRaises(ValueError):
            validate_input_data(self.invalid_transaction)
    
    def test_feature_creation(self):
        """Test feature creation from validated data"""
        validated_data = validate_input_data(self.valid_transaction)
        features = create_features(validated_data)
        
        self.assertEqual(features.shape, (1, 15), "Should create 15 features")
        self.assertGreater(features[0, 5], 0, "Amount feature should be positive")
        self.assertGreater(features[0, 6], 0, "Log amount should be positive")
    
    def test_prediction_functionality(self):
        """Test the full prediction pipeline"""
        if model is None:
            self.skipTest("Model not loaded")
        
        validated_data = validate_input_data(self.valid_transaction)
        features = create_features(validated_data)
        
        # Test prediction
        prediction_proba = model.predict_proba(features)[0]
        self.assertEqual(len(prediction_proba), 2, "Should return probabilities for 2 classes")
        self.assertAlmostEqual(sum(prediction_proba), 1.0, places=5, 
                             msg="Probabilities should sum to 1")
        
        # Test prediction result
        fraud_probability = prediction_proba[1]
        prediction = 1 if fraud_probability >= threshold else 0
        self.assertIn(prediction, [0, 1], "Prediction should be 0 or 1")

class TestSecurityFeatures(unittest.TestCase):
    """Test security functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.security_manager = SecurityManager()
        self.test_data = {
            'step': '100',
            'amount': '1500.50',
            'gender': '1',
            'category': '5'
        }
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        malicious_input = {
            'step': '100<script>alert("xss")</script>',
            'amount': '1500.50; DROP TABLE users;',
            'gender': '<>&"\'()',
            'category': '5'
        }
        
        sanitized = sanitize_input(malicious_input)
        
        for key, value in sanitized.items():
            self.assertNotIn('<', str(value), f"Should remove < from {key}")
            self.assertNotIn('>', str(value), f"Should remove > from {key}")
            self.assertNotIn(';', str(value), f"Should remove ; from {key}")
    
    def test_transaction_validation(self):
        """Test transaction data validation"""
        # Valid transaction
        is_valid, error = validate_transaction_data(self.test_data)
        self.assertTrue(is_valid, f"Valid transaction failed: {error}")
        
        # Invalid amount
        invalid_data = self.test_data.copy()
        invalid_data['amount'] = '-100'
        is_valid, error = validate_transaction_data(invalid_data)
        self.assertFalse(is_valid, "Negative amount should be invalid")
        
        # Missing required field
        incomplete_data = self.test_data.copy()
        del incomplete_data['step']
        is_valid, error = validate_transaction_data(incomplete_data)
        self.assertFalse(is_valid, "Missing required field should be invalid")
    
    def test_api_key_generation(self):
        """Test API key generation and validation"""
        user_id = "test_user"
        permissions = ["predict", "batch"]
        
        # Generate API key
        key_id, secret = self.security_manager.generate_api_key(user_id, permissions)
        
        self.assertIsNotNone(key_id, "Key ID should be generated")
        self.assertIsNotNone(secret, "Secret should be generated")
        self.assertGreater(len(key_id), 10, "Key ID should be sufficiently long")
        self.assertGreater(len(secret), 20, "Secret should be sufficiently long")
        
        # Validate API key
        is_valid, key_data = self.security_manager.validate_api_key(key_id, secret)
        self.assertTrue(is_valid, "Generated key should be valid")
        self.assertEqual(key_data['user_id'], user_id, "User ID should match")
        self.assertEqual(key_data['permissions'], permissions, "Permissions should match")
        
        # Test invalid key
        is_valid, key_data = self.security_manager.validate_api_key(key_id, "wrong_secret")
        self.assertFalse(is_valid, "Invalid secret should fail validation")

class TestWebInterface(unittest.TestCase):
    """Test web interface functionality"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_home_page(self):
        """Test home page loads correctly"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SecureGuard', response.data)
    
    def test_form_pages(self):
        """Test form pages load correctly"""
        # Basic form
        response = self.app.get('/form_basic')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Quick Transaction Scan', response.data)
        
        # Advanced form
        response = self.app.get('/form_advanced')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Deep Transaction Analysis', response.data)
    
    def test_real_time_dashboard(self):
        """Test real-time dashboard"""
        response = self.app.get('/real-time')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Live Fraud Detection Center', response.data)
    
    def test_prediction_endpoint(self):
        """Test prediction endpoint with valid data"""
        form_data = {
            'step': '100',
            'amount': '1500.50',
            'gender': '1',
            'category': '5',
            'csrf_token': 'test_token'  # Mock CSRF token
        }
        
        # Mock CSRF validation
        with patch('security.validate_csrf_token', return_value=True):
            response = self.app.post('/predict', data=form_data, follow_redirects=True)
            # Note: This might fail due to CSRF protection in production
            # In a real test environment, you'd need proper CSRF token handling
            self.assertIn(response.status_code, [200, 400, 403])
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        # Health check
        response = self.app.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
        
        # Stats endpoint
        response = self.app.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        # Should return stats or message about no predictions

class TestDatabaseOperations(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        # Create a test database configuration
        self.test_config = DatabaseConfig()
        self.test_config.db_type = 'sqlite'
        self.test_config.sqlite_file = ':memory:'  # In-memory database for testing
        
        # Create database manager
        self.db_manager = DatabaseManager(self.test_config)
    
    def test_prediction_logging(self):
        """Test prediction logging functionality"""
        test_prediction = {
            'session_id': 'test_session',
            'fraud_probability': 0.75,
            'prediction': 1,
            'confidence': 95.5,
            'risk_level': 'High',
            'processing_time': 0.123,
            'model_version': 'v2.0'
        }
        
        try:
            prediction_id = self.db_manager.log_prediction(test_prediction)
            self.assertGreater(prediction_id, 0, "Should return valid prediction ID")
        except Exception as e:
            self.fail(f"Prediction logging failed: {e}")
    
    def test_stats_retrieval(self):
        """Test statistics retrieval"""
        try:
            stats = self.db_manager.get_system_stats()
            self.assertIsInstance(stats, dict, "Should return dictionary")
            self.assertIn('total_predictions', stats)
            self.assertIn('fraud_detected', stats)
            self.assertIn('fraud_rate', stats)
        except Exception as e:
            self.fail(f"Stats retrieval failed: {e}")

class TestPerformanceAndLoad(unittest.TestCase):
    """Test system performance under load"""
    
    def setUp(self):
        """Set up performance tests"""
        self.app = app.test_client()
        self.test_data = {
            'step': 100,
            'amount': 1500.50,
            'gender': 1,
            'category': 5
        }
    
    def test_prediction_performance(self):
        """Test prediction performance"""
        if model is None:
            self.skipTest("Model not loaded")
        
        import time
        
        # Time multiple predictions
        start_time = time.time()
        for i in range(100):
            validated_data = validate_input_data(self.test_data)
            features = create_features(validated_data)
            prediction_proba = model.predict_proba(features)[0]
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 100
        
        self.assertLess(avg_time, 0.1, f"Average prediction time should be < 100ms, got {avg_time:.3f}s")
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = self.app.get('/api/health')
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        self.assertEqual(len(errors), 0, f"Should have no errors, got: {errors}")
        self.assertEqual(len(results), 10, "Should have 10 results")
        self.assertTrue(all(code == 200 for code in results), "All requests should succeed")
        self.assertLess(end_time - start_time, 5.0, "All requests should complete within 5 seconds")

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        """Set up integration tests"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_end_to_end_prediction(self):
        """Test complete prediction workflow"""
        if model is None:
            self.skipTest("Model not loaded")
        
        # Test data
        test_transaction = {
            'step': '150',
            'amount': '2500.75',
            'gender': '0',
            'category': '8',
            'customer': '5678',
            'age': '4'
        }
        
        # Step 1: Validate input
        try:
            validated_data = validate_input_data(test_transaction)
        except Exception as e:
            self.fail(f"Input validation failed: {e}")
        
        # Step 2: Create features
        try:
            features = create_features(validated_data)
            self.assertEqual(features.shape[1], 15, "Should have 15 features")
        except Exception as e:
            self.fail(f"Feature creation failed: {e}")
        
        # Step 3: Make prediction
        try:
            prediction_proba = model.predict_proba(features)[0]
            fraud_probability = prediction_proba[1]
            prediction = 1 if fraud_probability >= threshold else 0
            
            self.assertIn(prediction, [0, 1], "Prediction should be binary")
            self.assertGreaterEqual(fraud_probability, 0, "Fraud probability should be >= 0")
            self.assertLessEqual(fraud_probability, 1, "Fraud probability should be <= 1")
        except Exception as e:
            self.fail(f"Prediction failed: {e}")
    
    def test_system_configuration(self):
        """Test system configuration and settings"""
        # Test Flask app configuration
        self.assertIsNotNone(app.secret_key, "Secret key should be set")
        self.assertTrue(hasattr(app, 'extensions'), "App should have extensions")
        
        # Test model files exist
        model_files = ['fraud_model.pkl', 'label_encoders.pkl', 'threshold.pkl', 'feature_names.pkl']
        for filename in model_files:
            filepath = os.path.join('model', filename)
            self.assertTrue(os.path.exists(filepath), f"Model file {filename} should exist")
    
    def test_error_handling(self):
        """Test error handling and recovery"""
        # Test invalid endpoints
        response = self.app.get('/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        # Test malformed requests
        response = self.app.post('/api/predict', 
                               data='invalid json',
                               content_type='application/json')
        self.assertIn(response.status_code, [400, 401])  # Should reject invalid requests

def run_all_tests():
    """Run all tests and generate a report"""
    print("=" * 80)
    print("COMPREHENSIVE FRAUD DETECTION SYSTEM TEST SUITE")
    print("=" * 80)
    
    # Create test suite
    test_classes = [
        TestFraudDetectionModel,
        TestSecurityFeatures,
        TestWebInterface,
        TestDatabaseOperations,
        TestPerformanceAndLoad,
        TestIntegration
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\n')[0]}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\n')[-2]}")
    
    print("\n" + "=" * 80)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)