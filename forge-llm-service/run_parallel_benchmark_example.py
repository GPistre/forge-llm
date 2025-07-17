#!/usr/bin/env python3

"""
Example script showing how to use the parallel benchmark functionality.

This script demonstrates how to run parallel simulations for faster benchmarking
when testing LLM vs AI performance.
"""

import os
import sys
import subprocess

def main():
    # Example usage of the parallel benchmark
    
    # Paths (adjust these to your setup)
    forge_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Example decks - use any Commander decks you have
    deck1 = "deck1.dck"  # Change to your actual deck name/path
    deck2 = "deck2.dck"  # Change to your actual deck name/path
    
    # Benchmark parameters
    num_sims = 10  # Number of games per configuration
    max_workers = 4  # Number of parallel processes
    output_dir = "benchmark_results"
    
    print("========================================")
    print("Parallel Forge LLM Benchmark Example")
    print("========================================")
    print(f"Deck 1: {deck1}")
    print(f"Deck 2: {deck2}")
    print(f"Games per configuration: {num_sims}")
    print(f"Parallel workers: {max_workers}")
    print(f"Output directory: {output_dir}")
    print("========================================")
    
    # Command to run the benchmark
    cmd = [
        "python3", "run_benchmark.py",
        deck1, deck2,
        "--num-sims", str(num_sims),
        "--max-workers", str(max_workers),
        "--forge-path", forge_path,
        "--output-dir", output_dir
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("\nStarting parallel benchmark...")
    
    try:
        # Run the benchmark
        result = subprocess.run(cmd, check=True, cwd=os.path.dirname(__file__))
        
        print("\n========================================")
        print("Benchmark completed successfully!")
        print(f"Results saved to: {output_dir}/")
        print("Check the following files:")
        print(f"  - {output_dir}/benchmark_results.json")
        print(f"  - {output_dir}/deck1_ai_vs_deck2_llm.log")
        print(f"  - {output_dir}/deck1_llm_vs_deck2_ai.log")
        print("========================================")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError running benchmark: {e}")
        print("Make sure:")
        print("1. The LLM service is running on localhost:7861")
        print("2. The deck files exist and are valid")
        print("3. Forge is properly built")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()