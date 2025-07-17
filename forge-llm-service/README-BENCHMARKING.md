# Forge MTG LLM Benchmarking

This tool allows you to benchmark the performance of the LLM-powered AI against the traditional Forge AI in Magic: The Gathering matches.

## Prerequisites

- Python 3.6 or higher
- Forge MTG built with the LLM integration
- Running LLM server (test_server.py or equivalent)

## How to Use

1. Ensure your LLM server is running:
   ```bash
   cd forge-llm-service
   python test_server.py
   ```

2. In a new terminal, run the benchmark script:
   ```bash
   cd forge-llm-service
   python run_benchmark.py <deck1> <deck2> [options]
   ```

### Command-Line Arguments

- `deck1`: Path or name of the first deck
- `deck2`: Path or name of the second deck
- `-n, --num-sims`: Number of games to simulate per configuration (default: 5)
- `-f, --forge-path`: Path to the Forge installation (default: parent directory)
- `-o, --output-dir`: Directory to save output files (optional)

Note: The script always uses Commander format for the simulations.

### Example Usage

```bash
# Using deck names (from the decks directory)
python run_benchmark.py "mono-red.dck" "mono-blue.dck" -n 10

# Using full paths with output directory
python run_benchmark.py "/path/to/deck1.dck" "/path/to/deck2.dck" -n 20 -o ./benchmark-results
```

## Understanding the Results

The benchmark will run multiple configurations to test each deck with both the traditional AI and the LLM-powered AI:

1. Deck1(AI) vs Deck2(LLM)
2. Deck1(LLM) vs Deck2(AI)

For each configuration, the script will:
- Run the specified number of games
- Track wins for each player
- Calculate win rates and other statistics
- Output a summary to the console

If an output directory is specified, detailed logs and a JSON file with results will be saved.

## Example Output

```
=== Running configuration: Deck1(AI) vs Deck2(LLM) ===
[Simulation output]

Results for Deck1(AI) vs Deck2(LLM):
  Ai(1)-mono-red: 7 wins (70.0%)
  LLM(2)-mono-blue: 3 wins (30.0%)

=== Running configuration: Deck1(LLM) vs Deck2(AI) ===
[Simulation output]

Results for Deck1(LLM) vs Deck2(AI):
  LLM(1)-mono-red: 4 wins (40.0%)
  Ai(2)-mono-blue: 6 wins (60.0%)

=== Overall Benchmark Results ===
Total games: 20
Deck 1 wins: 11 (55.0%)
Deck 2 wins: 9 (45.0%)
```

## Troubleshooting

1. **"Address already in use" error**: The LLM server is already running on the default port. Either use the existing server or stop it and restart.

2. **"No such file or directory" error**: Check the paths to your decks. If using deck names, make sure they exist in the Forge decks directory.

3. **Simulations hang**: Check that the Forge application is properly built and that the LLM server is responding correctly.

4. **Java class not found**: Ensure that Forge is properly compiled and the classpath in the script points to the correct locations.

## Advanced Usage

### Testing Different Models

To benchmark different LLM models, modify the LLM server to use different models and run the benchmark script against each configuration.

### Custom Analysis

The benchmark results are saved in JSON format, which allows for custom analysis using your preferred tools.

```json
{
  "configurations": {
    "Deck1(AI) vs Deck2(LLM)": {
      "wins": {
        "Ai(1)-mono-red": 7,
        "LLM(2)-mono-blue": 3
      },
      "draws": 0,
      "games": 10
    },
    "Deck1(LLM) vs Deck2(AI)": {
      "wins": {
        "LLM(1)-mono-red": 4,
        "Ai(2)-mono-blue": 6
      },
      "draws": 0,
      "games": 10
    }
  },
  "summary": {
    "total_games": 20,
    "deck1_wins": 11,
    "deck2_wins": 9,
    "draws": 0,
    "deck1_win_percentage": 55.0,
    "deck2_win_percentage": 45.0,
    "draw_percentage": 0.0
  }
}
```