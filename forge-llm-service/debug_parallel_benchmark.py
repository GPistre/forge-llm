#!/usr/bin/env python3

"""
Debug version of parallel benchmark to identify hanging issues.
"""

import subprocess
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def debug_run_single_game(deck1, deck2, controllers, unique_id, forge_path):
    """Debug version of single game runner with extensive logging."""
    
    thread_id = threading.current_thread().ident
    print(f"[Thread {thread_id}] Starting game {unique_id}")
    
    cmd = [
        "java",
        "-Dllm.endpoint=http://localhost:7861",
        "-Djava.net.preferIPv4Stack=true",
        f"-Dgame.id={unique_id}",
        "-jar", f"{forge_path}/forge-gui-desktop/target/forge-gui-desktop-2.0.04-SNAPSHOT-jar-with-dependencies.jar",
        "sim",
        "-f", 'Commander',
        "-d", deck1, deck2,
        "-n", "1",
        "-c", ",".join(controllers),
        "-q"
    ]
    
    print(f"[Thread {thread_id}] Command: {' '.join(cmd)}")
    
    start_time = time.time()
    process = None
    
    try:
        print(f"[Thread {thread_id}] Creating subprocess...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        print(f"[Thread {thread_id}] Subprocess created with PID {process.pid}")
        
        # Wait for completion with timeout
        print(f"[Thread {thread_id}] Waiting for process to complete...")
        stdout, stderr = process.communicate(timeout=180)  # 3 minute timeout
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"[Thread {thread_id}] Process completed in {duration:.2f}s, return code: {process.returncode}")
        
        if process.returncode != 0:
            print(f"[Thread {thread_id}] ERROR: {stderr}")
            return None
        
        print(f"[Thread {thread_id}] Success, output length: {len(stdout)} chars")
        return stdout
        
    except subprocess.TimeoutExpired:
        print(f"[Thread {thread_id}] TIMEOUT after 3 minutes")
        if process:
            print(f"[Thread {thread_id}] Killing process {process.pid}")
            process.kill()
            process.wait()
        return None
        
    except Exception as e:
        print(f"[Thread {thread_id}] EXCEPTION: {e}")
        if process:
            try:
                print(f"[Thread {thread_id}] Cleaning up process {process.pid}")
                process.kill()
                process.wait()
            except:
                pass
        return None
        
    finally:
        if process and process.poll() is None:
            print(f"[Thread {thread_id}] Final cleanup of process {process.pid}")
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                    process.wait()
                except:
                    pass

def debug_parallel_test(deck1, deck2, num_games=3, max_workers=2):
    """Run a small parallel test with debug output."""
    
    import os
    forge_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"Starting debug parallel test:")
    print(f"  Forge path: {forge_path}")
    print(f"  Deck 1: {deck1}")
    print(f"  Deck 2: {deck2}")
    print(f"  Games: {num_games}")
    print(f"  Max workers: {max_workers}")
    print()
    
    # Create tasks
    tasks = []
    for i in range(num_games):
        short_uuid = str(uuid.uuid4())[:8]
        unique_id = f"g{i+1}_{short_uuid}"
        controllers = ["ai", "ai"]
        tasks.append((deck1, deck2, controllers, unique_id, forge_path))
        print(f"Task {i+1}: {unique_id} with {controllers}")
    
    print(f"\nStarting {len(tasks)} tasks with {max_workers} workers...")
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        print("Submitting tasks...")
        
        # Submit all tasks
        future_to_id = {}
        for i, task in enumerate(tasks):
            future = executor.submit(debug_run_single_game, *task)
            future_to_id[future] = task[3]  # unique_id
            print(f"Submitted task {i+1}: {task[3]}")
        
        print(f"All {len(tasks)} tasks submitted, waiting for completion...")
        
        # Collect results
        completed = 0
        try:
            for future in as_completed(future_to_id, timeout=300):  # 5 minute total timeout
                unique_id = future_to_id[future]
                completed += 1
                
                try:
                    result = future.result(timeout=10)
                    print(f"Task {unique_id} completed ({completed}/{len(tasks)})")
                    if result:
                        results.append(result)
                    else:
                        print(f"Task {unique_id} returned no output")
                        
                except Exception as e:
                    print(f"Task {unique_id} failed: {e}")
                    
        except Exception as e:
            print(f"Error in parallel execution: {e}")
            
            # Check status of remaining futures
            for future, unique_id in future_to_id.items():
                if not future.done():
                    print(f"Task {unique_id} is still running, cancelling...")
                    future.cancel()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\nDebug test completed:")
    print(f"  Total time: {total_time:.2f} seconds")
    print(f"  Completed tasks: {completed}/{len(tasks)}")
    print(f"  Successful results: {len(results)}")
    
    return results

if __name__ == "__main__":
    # Test with small numbers to debug
    print("=" * 60)
    print("DEBUG PARALLEL BENCHMARK TEST")
    print("=" * 60)
    
    # Use actual deck names from your system
    deck1 = "zinnia.dck"  # Change to actual deck name
    deck2 = "zinnia.dck"  # Change to actual deck name
    
    try:
        results = debug_parallel_test(deck1, deck2, num_games=3, max_workers=2)
        
        if results:
            print(f"\n✓ Debug test successful with {len(results)} results")
            print("First result preview:")
            print(results[0][:200] + "..." if len(results[0]) > 200 else results[0])
        else:
            print("\n✗ Debug test failed - no results")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()