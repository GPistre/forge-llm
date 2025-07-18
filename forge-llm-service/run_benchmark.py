#!/usr/bin/env python3
import argparse
import subprocess
import re
import os
import sys
import json
from collections import defaultdict
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

# Regular expression to extract game results from logs
GAME_RESULT_REGEX = r"Game Result: Game \d+ ended in \d+ ms\. (.*?) has won!"
DRAW_RESULT_REGEX = r"Game Result: Game \d+ ended in a Draw!"

class ForgeSimulator:
    def __init__(self, forge_path):
        self.forge_path = forge_path
        
    def run_simulation(self, deck1, deck2, num_games, controllers, log_file=None, game_id=None):
        """
        Run a simulation with the specified decks, number of games, and controller types.
        
        Args:
            deck1: Path or name of the first deck
            deck2: Path or name of the second deck
            num_games: Number of games to simulate
            controllers: List of controller types (e.g., ['ai', 'llm'])
            log_file: Optional file to save the output
            game_id: Unique identifier for this game to avoid player name conflicts
        
        Returns:
            The raw output of the simulation
        """
        # Construct the command using the same approach as run_llm_simulation.sh
        cmd = [
            "java",
            "-Dllm.endpoint=http://localhost:7861",
            "-Djava.net.preferIPv4Stack=true",
        ]
        
        # Add unique game identifier to avoid player name conflicts in parallel runs
        if game_id:
            cmd.extend(["-Dgame.id=" + str(game_id)])
        
        cmd.extend([
            "-jar", f"{self.forge_path}/forge-gui-desktop/target/forge-gui-desktop-2.0.04-SNAPSHOT-jar-with-dependencies.jar",
            "sim",
            "-f", 'Commander',
            "-d", deck1, deck2,
            "-n", str(num_games),
            "-c", ",".join(controllers),
            "-q"  # Quiet mode, only show results
        ])
        
        # Only print command for single games to reduce noise in parallel mode
        if num_games == 1:
            print(f"Running simulation with command: {' '.join(cmd)}")
        
        # Run the simulation
        start_time = time.time()
        process = None
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered for better real-time output
            )
            
            # Use communicate() instead of reading line by line to avoid blocking
            stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout per game
            
            end_time = time.time()
            
            # Check for errors
            if process.returncode != 0:
                print(f"Error running simulation (return code {process.returncode}): {stderr}")
                return None
            
            # Save to log file if specified
            if log_file and stdout:
                with open(log_file, 'a') as f:
                    f.write(stdout)
            
            if num_games == 1:
                print(f"Single game simulation completed in {end_time - start_time:.2f} seconds")
            
            return stdout
            
        except subprocess.TimeoutExpired:
            print(f"Simulation timed out after 5 minutes")
            if process:
                process.kill()
                process.wait()
            return None
        except Exception as e:
            print(f"Exception during simulation: {e}")
            if process:
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
            return None
        finally:
            # Ensure process is cleaned up
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                        process.wait()
                    except:
                        pass

def parse_results(output):
    """
    Parse the simulation output to extract game results.
    
    Args:
        output: The raw output from the simulation
    
    Returns:
        Dictionary containing win counts and draws
    """
    if not output:
        return None
    
    results = {
        'wins': defaultdict(int),
        'draws': 0,
        'games': 0
    }
    
    # Find all win results
    win_matches = re.finditer(GAME_RESULT_REGEX, output)
    for match in win_matches:
        winner = match.group(1)
        results['wins'][winner] += 1
        results['games'] += 1
    
    # Find all draw results
    draw_matches = re.finditer(DRAW_RESULT_REGEX, output)
    for _ in draw_matches:
        results['draws'] += 1
        results['games'] += 1
    
    return results

def run_single_game(simulator, deck1, deck2, controllers, game_id, unique_id):
    """
    Run a single game simulation.
    
    Args:
        simulator: ForgeSimulator instance
        deck1: Path or name of the first deck
        deck2: Path or name of the second deck
        controllers: List of controller types (e.g., ['ai', 'llm'])
        game_id: Unique identifier for this game (for logging)
        unique_id: Short unique ID for Java system property
    
    Returns:
        Tuple of (game_id, output) where output is the raw simulation output
    """
    print(f"Starting game {game_id} with controllers {controllers}")
    output = simulator.run_simulation(deck1, deck2, 1, controllers, game_id=unique_id)
    print(f"Completed game {game_id}")
    return (game_id, output)

def run_benchmark(deck1, deck2, num_sims, forge_path, output_dir=None, max_workers=4):
    # Always use Commander format
    game_format = 'Commander'
    """
    Run the full benchmark for the given decks.
    
    Args:
        deck1: Path or name of the first deck
        deck2: Path or name of the second deck
        num_sims: Number of games to simulate per configuration
        forge_path: Path to the Forge installation
        output_dir: Directory to save output files
        max_workers: Maximum number of parallel simulation processes
    
    Returns:
        Dictionary containing all results
    """
    simulator = ForgeSimulator(forge_path)
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Define the configurations to test
    configs = [
        {"name": "Deck1(AI) vs Deck2(AI)", "controllers": ["ai", "ai"], "format": game_format, "log_file": os.path.join(output_dir, "deck1_ai_vs_deck2_ai.log") if output_dir else None},
        {"name": "Deck2(AI) vs Deck1(AI)", "controllers": ["ai", "ai"], "format": game_format, "log_file": os.path.join(output_dir, "deck2_ai_vs_deck1_ai.log") if output_dir else None},
    ]
    
    all_results = {}
    
    # Run each configuration in parallel
    for config in configs:
        print(f"\n=== Running configuration: {config['name']} ===")
        print(f"Running {num_sims} games in parallel with up to {max_workers} workers")
        
        # Create tasks for parallel execution
        tasks = []
        for i in range(num_sims):
            # Generate a short unique ID to avoid player name conflicts
            short_uuid = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID
            game_id = f"{config['name']}_game_{i+1}_{short_uuid}"
            unique_id = f"g{i+1}_{short_uuid}"  # Shorter ID for Java system property
            tasks.append((simulator, deck1, deck2, config['controllers'], game_id, unique_id))
        
        # Run simulations in parallel
        start_time = time.time()
        outputs = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_game = {
                executor.submit(run_single_game, *task): task[4] 
                for task in tasks
            }
            
            # Collect results as they complete with progress tracking
            completed_games = 0
            failed_games = 0
            
            try:
                # Use timeout for individual futures to prevent hanging
                for future in as_completed(future_to_game, timeout=600):  # 10 minutes total timeout
                    try:
                        game_id, output = future.result(timeout=30)  # 30 second timeout for result retrieval
                        completed_games += 1
                        print(f"Progress: {completed_games}/{num_sims} games completed")
                        
                        if output:
                            outputs.append(output)
                            
                            # Save individual game output to log file if specified
                            if config['log_file']:
                                try:
                                    with open(config['log_file'], 'a') as f:
                                        f.write(f"\n=== {game_id} ===\n")
                                        f.write(output)
                                        f.write(f"\n=== End {game_id} ===\n\n")
                                except IOError as e:
                                    print(f"Warning: Could not write to log file: {e}")
                        else:
                            print(f"Warning: No output received for {game_id}")
                            failed_games += 1
                            
                    except Exception as e:
                        game_id = future_to_game[future]
                        print(f"Error in {game_id}: {e}")
                        completed_games += 1
                        failed_games += 1
                        
            except Exception as e:
                print(f"Error in parallel execution: {e}")
                
                # Cancel remaining futures
                for future in future_to_game:
                    if not future.done():
                        future.cancel()
                        
            print(f"Parallel execution completed: {completed_games} total, {failed_games} failed")
        
        end_time = time.time()
        print(f"Completed {len(outputs)} games in {end_time - start_time:.2f} seconds")
        
        # Combine all outputs and parse results
        if outputs:
            combined_output = '\n'.join(outputs)
            results = parse_results(combined_output)
            all_results[config['name']] = results
            
            # Print summary for this configuration
            print(f"\nResults for {config['name']}:")
            if results['games'] > 0:
                for winner, count in results['wins'].items():
                    print(f"  {winner}: {count} wins ({count/results['games']*100:.1f}%)")
                if results['draws'] > 0:
                    print(f"  Draws: {results['draws']} ({results['draws']/results['games']*100:.1f}%)")
            else:
                print("  No valid game results found")
        else:
            print(f"Failed to get any results for {config['name']}")
    
    # Calculate overall statistics
    if all_results:
        print("\n=== Overall Benchmark Results ===")
        
        deck1_wins = 0
        deck2_wins = 0
        total_games = 0
        total_draws = 0
        
        # Extract deck names from result keys
        for config_name, results in all_results.items():
            for winner, count in results['wins'].items():
                # Handle player names with unique suffixes (e.g., "LLM(1)-DeckName-g1_abc123")
                if ("Ai(1)" in winner or "LLM(1)" in winner) and not ("Ai(10)" in winner or "LLM(10)" in winner):  # Deck 1
                    deck1_wins += count
                elif ("Ai(2)" in winner or "LLM(2)" in winner) and not ("Ai(20)" in winner or "LLM(20)" in winner):  # Deck 2
                    deck2_wins += count
                    
            total_draws += results['draws']
            total_games += results['games']
        
        # Print overall stats
        print(f"Total games: {total_games}")
        if total_games > 0:
            print(f"Deck 1 wins: {deck1_wins} ({deck1_wins/total_games*100:.1f}%)")
            print(f"Deck 2 wins: {deck2_wins} ({deck2_wins/total_games*100:.1f}%)")
            if total_draws > 0:
                print(f"Draws: {total_draws} ({total_draws/total_games*100:.1f}%)")
        
        # Save the results to a JSON file if output directory is specified
        if output_dir:
            results_file = os.path.join(output_dir, "benchmark_results.json")
            with open(results_file, 'w') as f:
                json.dump({
                    "configurations": all_results,
                    "summary": {
                        "total_games": total_games,
                        "deck1_wins": deck1_wins,
                        "deck2_wins": deck2_wins,
                        "draws": total_draws,
                        "deck1_win_percentage": deck1_wins/total_games*100 if total_games > 0 else 0,
                        "deck2_win_percentage": deck2_wins/total_games*100 if total_games > 0 else 0,
                        "draw_percentage": total_draws/total_games*100 if total_games > 0 else 0
                    }
                }, f, indent=2)
            print(f"Results saved to {results_file}")
    
    return all_results

def main():
    parser = argparse.ArgumentParser(description='Run Forge MTG deck simulations to compare AI vs LLM performance')
    parser.add_argument('deck1', help='Path or name of the first deck')
    parser.add_argument('deck2', help='Path or name of the second deck')
    parser.add_argument('-n', '--num-sims', type=int, default=5, help='Number of games to simulate per configuration')
    parser.add_argument('-f', '--forge-path', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                        help='Path to the Forge installation')
    parser.add_argument('-o', '--output-dir', help='Directory to save output files')
    parser.add_argument('-w', '--max-workers', type=int, default=4, 
                        help='Maximum number of parallel simulation processes (default: 4)')
        # Always use Commander format
    
    args = parser.parse_args()
    
    # Verify the jar file exists
    jar_path = f"{args.forge_path}/forge-gui-desktop/target/forge-gui-desktop-2.0.04-SNAPSHOT-jar-with-dependencies.jar"
    if not os.path.exists(jar_path):
        print(f"Error: Could not find Forge jar file at {jar_path}")
        print("Make sure Forge is properly built with the jar-with-dependencies target.")
        sys.exit(1)
    
    run_benchmark(args.deck1, args.deck2, args.num_sims, args.forge_path, args.output_dir, args.max_workers)

if __name__ == '__main__':
    main()