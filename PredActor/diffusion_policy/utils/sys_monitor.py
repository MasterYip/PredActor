import psutil
import sys
import os

def check_ram_usage(phase_name: str = "RAM Usage", max_gb: float = 50.0):
    """
    Check current RAM usage and kill program if it exceeds max_gb.
    
    Args:
        phase_name: Name of the current phase (for debugging)
        max_gb: Maximum allowed RAM in GB (default: 50GB)
    """
    process = psutil.Process(os.getpid())
    ram_usage_bytes = process.memory_info().rss
    ram_usage_gb = ram_usage_bytes / (1024 ** 3)
    
    print(f"[RAM DEBUG] {phase_name}: {ram_usage_gb:.2f} GB")
    
    if ram_usage_gb > max_gb:
        print(f"[RAM ERROR] Memory usage ({ram_usage_gb:.2f} GB) exceeds limit ({max_gb} GB)!")
        print(f"[RAM ERROR] Killing program to prevent system crash...")
        sys.exit(1)
    
    return ram_usage_gb
