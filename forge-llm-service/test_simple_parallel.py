#!/usr/bin/env python3

"""
Simple test to debug parallel execution hanging.
"""

import subprocess
import time
import uuid
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_single_debug_game(deck1, deck2, unique_id):
    """Run a single game with full debug output."""
    
    forge_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    cmd = [
        "java",
        "-Dllm.endpoint=http://localhost:7861",
        "-Djava.net.preferIPv4Stack=true",
        f"-Dgame.id={unique_id}",
        "-jar", f"{forge_path}/forge-gui-desktop/target/forge-gui-desktop-2.0.04-SNAPSHOT-jar-with-dependencies.jar",
        "sim",
        "-f", "Commander",
        "-d", deck1, deck2,
        "-n", "1",
        "-c", "ai,ai",  # Use AI vs AI to avoid LLM service issues
        "-q"
    ]
    
    print(f"🎮 Starting game {unique_id}")
    print(f"   Command: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes max
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Game {unique_id} completed in {duration:.1f}s")
        
        if result.returncode != 0:
            print(f"❌ Game {unique_id} failed with return code {result.returncode}")
            print(f"   STDERR: {result.stderr[:200]}...")
            return None
        
        return result.stdout
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Game {unique_id} timed out after 3 minutes")
        return None
    except Exception as e:
        print(f"💥 Game {unique_id} crashed: {e}")
        return None

def test_sequential():
    """Test running games sequentially first."""
    print("=" * 50)
    print("TESTING SEQUENTIAL EXECUTION")
    print("=" * 50)
    
    deck1 = "zinnia.dck"  # Change to your deck
    deck2 = "zinnia.dck"
    
    results = []
    for i in range(2):
        unique_id = f"seq_{i+1}_{str(uuid.uuid4())[:6]}"
        result = run_single_debug_game(deck1, deck2, unique_id)
        if result:
            results.append(result)
        time.sleep(1)  # Small delay between games
    
    print(f"\nSequential test: {len(results)}/2 games succeeded")
    return len(results) == 2

def test_parallel():
    """Test running games in parallel."""
    print("=" * 50)
    print("TESTING PARALLEL EXECUTION")
    print("=" * 50)
    
    deck1 = "zinnia.dck"  # Change to your deck
    deck2 = "zinnia.dck"
    
    tasks = []
    for i in range(2):
        unique_id = f"par_{i+1}_{str(uuid.uuid4())[:6]}"
        tasks.append((deck1, deck2, unique_id))
    
    print(f"Running {len(tasks)} games in parallel...")
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit tasks
        futures = [executor.submit(run_single_debug_game, *task) for task in tasks]
        
        # Wait for completion
        try:
            for i, future in enumerate(as_completed(futures, timeout=300)):
                try:
                    result = future.result(timeout=10)
                    if result:
                        results.append(result)
                    print(f"🏁 Task {i+1} finished")
                except Exception as e:
                    print(f"❌ Task {i+1} failed: {e}")
        except Exception as e:
            print(f"💥 Parallel execution failed: {e}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\nParallel test: {len(results)}/2 games succeeded in {total_time:.1f}s")
    return len(results) == 2

def main():
    """Run both tests."""
    print("🔍 DEBUGGING PARALLEL EXECUTION HANG")
    print(f"📅 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if LLM server is running (optional)
    try:
        import requests
        response = requests.get("http://localhost:7861", timeout=2)
        print("🟢 LLM server appears to be running")
    except:
        print("🔴 LLM server not responding (using AI vs AI)")
    
    print()
    
    # Test sequential first
    sequential_ok = test_sequential()
    
    if not sequential_ok:
        print("❌ Sequential test failed - check deck names and Forge build")
        return
    
    print("\n" + "="*50)
    input("✅ Sequential test passed. Press Enter to test parallel...")
    
    # Test parallel
    parallel_ok = test_parallel()
    
    if parallel_ok:
        print("🎉 Both sequential and parallel tests passed!")
    else:
        print("❌ Parallel test failed - this confirms the hanging issue")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()