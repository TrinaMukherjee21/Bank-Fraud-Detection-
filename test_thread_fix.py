from threadpoolctl import threadpool_limits
import time
import sys

print("DEBUG: Applying thread limits (max 1)...")
with threadpool_limits(limits=1):
    print("DEBUG: Thread limits applied. Testing sklearn import...")
    start = time.time()
    try:
        from sklearn.preprocessing import LabelEncoder
        end = time.time()
        print(f"DEBUG: sklearn import OK ({end-start:.2f}s)")
        
        print("DEBUG: Testing xgboost import...")
        import xgboost
        print(f"DEBUG: xgboost import OK ({time.time()-end:.2f}s)")
        
        print("ALL CRITICAL IMPORTS SUCCESSFUL WITH THREAD LIMITS!")
    except Exception as e:
        print(f"FAILED: {e}")

print("Test finished.")
