import sys
import time

def test_import(module_name):
    print(f"Testing import: {module_name}...", end=" ", flush=True)
    start = time.time()
    try:
        __import__(module_name)
        end = time.time()
        print(f"OK ({end-start:.2f}s)")
    except Exception as e:
        print(f"FAILED: {e}")

modules = [
    "os", "logging", "datetime", "uuid", "json", "collections",
    "flask", "flask_login", "joblib", "numpy", "pandas", "sklearn",
    "xgboost"
]

for m in modules:
    test_import(m)

print("\nTesting local imports:")
# For local imports, we need to add path
sys.path.append(".")
test_import("utils.preprocess")
test_import("utils.auth")
test_import("models.user")

print("\nAll tests finished.")
