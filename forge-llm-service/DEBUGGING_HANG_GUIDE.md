# Debugging Parallel Execution Hang

## Problem
Parallel simulations hang after 2 games complete, with no activity on either the Python script or LLM server side.

## Diagnosis Steps

### Step 1: Check System Resources

Run this in a separate terminal while the hang occurs:

```bash
cd forge-llm-service
python3 check_resources.py monitor
```

Look for:
- Memory usage climbing continuously 
- Multiple Java processes that don't exit
- High number of network connections

### Step 2: Test Sequential vs Parallel

Run the simplified test:

```bash
cd forge-llm-service
python3 test_simple_parallel.py
```

This will:
1. Test 2 games sequentially (should work)
2. Test 2 games in parallel (may hang)
3. Use AI vs AI to eliminate LLM service issues

### Step 3: Run Debug Version

Use the debug benchmark with verbose output:

```bash
cd forge-llm-service 
python3 debug_parallel_benchmark.py
```

This shows detailed thread activity and process lifecycle.

### Step 4: Check Java Process Status

When hanging, check what Java processes are doing:

```bash
# List Java processes
ps aux | grep java

# Check if they're consuming CPU
top -p <java_pid>

# Check thread status (if available)
jstack <java_pid>
```

## Likely Causes & Fixes

### 1. Process Not Terminating Properly

**Symptom**: Java processes remain running after Python thinks they're done.

**Fix Applied**: Updated `run_benchmark.py` with:
- Better process cleanup in `finally` blocks
- `communicate()` instead of line-by-line reading
- Explicit `kill()` and `wait()` calls
- Timeout handling

### 2. Thread Pool Deadlock

**Symptom**: ThreadPoolExecutor hangs waiting for futures that never complete.

**Fix Applied**: Added:
- Timeout on `as_completed()`
- Timeout on `future.result()`
- Exception handling to cancel remaining futures

### 3. Resource Exhaustion

**Symptom**: System runs out of memory, file handles, or network connections.

**Check**:
```bash
# Memory usage
free -h

# Open file handles
lsof | grep java | wc -l

# Network connections
netstat -an | grep 7861
```

**Fix**: Reduce `max_workers` or add delays between game starts.

### 4. LLM Service Overwhelm

**Symptom**: LLM service stops responding to new connections.

**Check**: LLM service logs for errors or connection refused messages.

**Fix**: 
- Reduce parallel workers
- Add connection pooling
- Increase LLM service timeout

### 5. Java Initialization Issues

**Symptom**: Java processes start but hang during Forge initialization.

**Check**: Look for Java debug output showing where it stops.

**Fix**: 
- Increase Java heap size: `-Xmx4g`
- Disable problematic features: `-Djava.awt.headless=true`

## Debugging Commands

### Monitor Active Processes
```bash
# Watch Java processes in real-time
watch "ps aux | grep java"

# Monitor network connections to LLM service
watch "netstat -an | grep 7861"
```

### Kill Stuck Processes
```bash
# Kill all Java processes (if needed)
pkill -f "forge-gui-desktop"

# Kill specific process
kill -9 <pid>
```

### Check Python Thread Status
Add this to your Python script for debugging:
```python
import threading
print(f"Active threads: {threading.active_count()}")
for thread in threading.enumerate():
    print(f"  {thread.name}: {thread.is_alive()}")
```

## Improved Solutions

### Solution 1: Sequential with Limited Parallelism
Instead of full parallelism, run batches sequentially:

```python
def run_in_batches(tasks, batch_size=2):
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        run_parallel_batch(batch)
        time.sleep(5)  # Cooling period
```

### Solution 2: Process Pool Instead of Thread Pool
Use `ProcessPoolExecutor` to isolate Java processes:

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=2) as executor:
    # Same logic but with separate Python processes
```

### Solution 3: External Queue System
Use a job queue like Celery or RQ for better process management.

## Testing Your Fix

1. Run `test_simple_parallel.py` first
2. If that works, try `debug_parallel_benchmark.py`
3. Monitor resources with `check_resources.py monitor`
4. Finally test full benchmark with low numbers: `-n 4 -w 2`

## Emergency Stops

If system becomes unresponsive:

```bash
# Kill all Java processes
sudo pkill -f java

# Kill Python processes
sudo pkill -f python3

# Check for remaining processes
ps aux | grep -E "(java|python3)"
```