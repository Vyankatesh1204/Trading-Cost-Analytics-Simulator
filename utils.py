# utils.py

import time

def measure_latency(func):
    """Decorator to measure latency for trade simulation"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"Latency: {latency:.4f} ms")
        return result
    return wrapper
