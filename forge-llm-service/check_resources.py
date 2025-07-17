#!/usr/bin/env python3

"""
Check system resources during parallel execution.
"""

import psutil
import time
import subprocess

def check_system_resources():
    """Check and display current system resources."""
    
    # Memory info
    memory = psutil.virtual_memory()
    print(f"Memory: {memory.percent}% used ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)")
    
    # CPU info
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU: {cpu_percent}% used")
    
    # Find Java processes
    java_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
        try:
            if 'java' in proc.info['name'].lower():
                java_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if java_processes:
        print(f"\nJava processes: {len(java_processes)}")
        for proc in java_processes:
            try:
                memory_mb = proc.info['memory_info'].rss / 1024**2
                print(f"  PID {proc.info['pid']}: {memory_mb:.0f}MB RAM")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    else:
        print("\nNo Java processes found")
    
    # Check for hanging processes
    print(f"\nTotal processes: {len(list(psutil.process_iter()))}")

def monitor_during_execution():
    """Monitor resources while running a parallel benchmark."""
    
    print("Starting resource monitoring...")
    print("Run your parallel benchmark in another terminal")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            print("=" * 50)
            print(f"Time: {time.strftime('%H:%M:%S')}")
            check_system_resources()
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

def check_network_connections():
    """Check for hanging network connections."""
    
    print("\nChecking network connections to LLM service...")
    
    try:
        # Check connections to port 7861 (LLM service)
        connections = psutil.net_connections()
        llm_connections = [c for c in connections if c.laddr and c.laddr.port == 7861 or 
                          (c.raddr and c.raddr.port == 7861)]
        
        if llm_connections:
            print(f"Found {len(llm_connections)} connections to LLM service:")
            for conn in llm_connections:
                print(f"  {conn.status} - {conn.laddr} -> {conn.raddr}")
        else:
            print("No connections to LLM service found")
            
    except Exception as e:
        print(f"Could not check connections: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_during_execution()
    else:
        print("System Resource Check")
        print("=" * 30)
        check_system_resources()
        check_network_connections()
        print("\nTo monitor continuously during benchmark, run:")
        print("python3 check_resources.py monitor")