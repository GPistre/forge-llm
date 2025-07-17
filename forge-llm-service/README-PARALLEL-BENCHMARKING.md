# Parallel Benchmarking for Forge LLM Testing

This document describes the parallel benchmarking capabilities added to the Forge LLM service.

## Overview

The `run_benchmark.py` script has been enhanced to run simulations in parallel, significantly reducing the time needed for benchmarking LLM vs AI performance. Since most of the time is spent waiting for API calls to the LLM service, parallel execution provides substantial speedup.

## Key Features

- **Parallel Execution**: Run multiple games simultaneously using ThreadPoolExecutor
- **Unique Player Names**: Automatic generation of unique player identifiers to prevent conflicts
- **Progress Tracking**: Real-time progress updates as games complete
- **Configurable Workers**: Adjust the number of parallel processes based on your system
- **Individual Game Logging**: Each game's output is saved separately for detailed analysis
- **Error Handling**: Robust error handling for failed simulations
- **Combined Results**: Aggregated statistics across all parallel runs

## Usage

### Basic Usage

```bash
python3 run_benchmark.py deck1.dck deck2.dck -n 20 -w 8
```

### Advanced Usage with Output Directory

```bash
python3 run_benchmark.py deck1.dck deck2.dck \
    --num-sims 50 \
    --max-workers 6 \
    --output-dir benchmark_results \
    --forge-path /path/to/forge
```

### Parameters

- `deck1` and `deck2`: Deck names or file paths to compare
- `-n, --num-sims`: Number of games per configuration (default: 5)
- `-w, --max-workers`: Maximum parallel processes (default: 4)
- `-o, --output-dir`: Directory to save detailed logs and results
- `-f, --forge-path`: Path to Forge installation (auto-detected by default)

## Performance Improvements

### Before (Sequential)
- 10 games × 2 configurations = 20 total games
- Average game time: 60 seconds
- Total time: ~20 minutes

### After (Parallel with 4 workers)
- 10 games × 2 configurations = 20 total games  
- 4 games running simultaneously
- Total time: ~6 minutes (3-4x speedup)

## Output Files

When using `--output-dir`, the following files are created:

1. **benchmark_results.json**: Complete results in JSON format
2. **deck1_ai_vs_deck2_llm.log**: Detailed logs for AI vs LLM games
3. **deck1_llm_vs_deck2_ai.log**: Detailed logs for LLM vs AI games

### Sample JSON Output

```json
{
  "configurations": {
    "Deck1(AI) vs Deck2(LLM)": {
      "wins": {
        "Ai(1)-DeckName": 6,
        "LLM(2)-DeckName": 4
      },
      "draws": 0,
      "games": 10
    },
    "Deck1(LLM) vs Deck2(AI)": {
      "wins": {
        "LLM(1)-DeckName": 7,
        "Ai(2)-DeckName": 3
      },
      "draws": 0,
      "games": 10
    }
  },
  "summary": {
    "total_games": 20,
    "deck1_wins": 13,
    "deck2_wins": 7,
    "draws": 0,
    "deck1_win_percentage": 65.0,
    "deck2_win_percentage": 35.0,
    "draw_percentage": 0.0
  }
}
```

## Example Script

Use `run_parallel_benchmark_example.py` for a complete example:

```bash
python3 run_parallel_benchmark_example.py
```

Edit the deck names in the script before running.

## System Requirements

### Memory Considerations
- Each parallel Java process uses ~4GB RAM
- With 4 workers: ~16GB RAM recommended
- With 8 workers: ~32GB RAM recommended

### CPU Considerations
- LLM API calls are I/O bound, not CPU bound
- More workers = better utilization of API wait time
- Recommended: 2-8 workers depending on your LLM service capacity

### Network Considerations
- Each worker makes independent API calls to the LLM service
- Ensure your LLM service can handle concurrent requests
- Monitor LLM service response times with high concurrency

## Troubleshooting

### Common Issues

1. **OutOfMemoryError**
   - Reduce `--max-workers`
   - Increase system RAM
   - Use `-Xmx2g` in Java args to reduce per-process memory

2. **LLM Service Timeouts**
   - Reduce `--max-workers` to decrease load on LLM service
   - Check LLM service logs for capacity issues
   - Increase timeout values in LLMClient.java

3. **Player Name Conflicts (Fixed)**
   - The system now automatically generates unique player identifiers
   - Player names include a short UUID suffix (e.g., "LLM(1)-DeckName-g1_abc123")
   - No manual intervention needed for parallel runs

4. **Inconsistent Results**
   - Run more games (`--num-sims`) for statistical significance
   - Check for deck loading issues in logs
   - Verify LLM service stability

### Monitoring Progress

The script provides real-time progress updates:

```
=== Running configuration: Deck1(AI) vs Deck2(LLM) ===
Running 10 games in parallel with up to 4 workers
Starting game Deck1(AI) vs Deck2(LLM)_game_1 with controllers ['ai', 'llm']
Starting game Deck1(AI) vs Deck2(LLM)_game_2 with controllers ['ai', 'llm']
...
Progress: 1/10 games completed
Progress: 2/10 games completed
...
Completed 10 games in 156.78 seconds
```

## Best Practices

1. **Start Small**: Begin with 2-4 workers and increase based on performance
2. **Monitor Resources**: Watch RAM and CPU usage during runs
3. **LLM Service Health**: Ensure your LLM service is stable before large benchmarks
4. **Statistical Significance**: Run at least 20-50 games per configuration for reliable results
5. **Save Results**: Always use `--output-dir` for important benchmarks

## Integration with Existing Workflows

The parallel benchmark can be integrated into CI/CD pipelines or automated testing:

```bash
# Example CI script
#!/bin/bash
echo "Starting LLM performance benchmark..."
python3 run_benchmark.py tournament_deck1.dck tournament_deck2.dck \
    --num-sims 100 \
    --max-workers 8 \
    --output-dir "results/$(date +%Y%m%d_%H%M%S)"

# Check if LLM performance meets threshold
python3 analyze_results.py results/latest/benchmark_results.json
```

This parallel benchmarking capability makes it practical to run large-scale performance comparisons between AI and LLM controllers, enabling better evaluation of LLM integration quality.