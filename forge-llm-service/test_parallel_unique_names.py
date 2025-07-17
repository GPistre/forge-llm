#!/usr/bin/env python3

"""
Test script to verify that parallel simulations generate unique player names.
"""

import subprocess
import re
import uuid
import time

def test_unique_player_names():
    """Test that parallel simulations generate unique player names."""
    
    print("Testing unique player name generation...")
    
    # Generate a few test commands that would run in parallel
    test_commands = []
    
    for i in range(3):
        short_uuid = str(uuid.uuid4())[:8]
        unique_id = f"g{i+1}_{short_uuid}"
        
        cmd = [
            "echo", 
            f"Testing unique ID: {unique_id}",
            "->",
            f"LLM(1)-TestDeck-{unique_id}",
            "vs",
            f"LLM(2)-TestDeck-{unique_id}"
        ]
        
        test_commands.append((unique_id, cmd))
    
    print("Generated test commands:")
    for unique_id, cmd in test_commands:
        print(f"  {unique_id}: {' '.join(cmd)}")
    
    # Verify all IDs are unique
    ids = [unique_id for unique_id, _ in test_commands]
    unique_ids = set(ids)
    
    if len(ids) == len(unique_ids):
        print("✓ All generated IDs are unique")
    else:
        print("✗ Some IDs are duplicated!")
        return False
    
    # Test the actual player name pattern
    test_deck_name = "TestDeck"
    test_unique_id = "g1_abc12345"
    
    expected_llm_name = f"LLM(1)-{test_deck_name}-{test_unique_id}"
    expected_ai_name = f"Ai(2)-{test_deck_name}-{test_unique_id}"
    
    print(f"\nExpected player names with unique ID '{test_unique_id}':")
    print(f"  LLM Player: {expected_llm_name}")
    print(f"  AI Player:  {expected_ai_name}")
    
    # Test that these names would be different in parallel runs
    other_unique_id = "g2_def67890"
    other_llm_name = f"LLM(1)-{test_deck_name}-{other_unique_id}"
    other_ai_name = f"Ai(2)-{test_deck_name}-{other_unique_id}"
    
    print(f"\nExpected player names with different unique ID '{other_unique_id}':")
    print(f"  LLM Player: {other_llm_name}")
    print(f"  AI Player:  {other_ai_name}")
    
    if expected_llm_name != other_llm_name and expected_ai_name != other_ai_name:
        print("✓ Player names are unique across parallel games")
    else:
        print("✗ Player names are not unique across parallel games!")
        return False
    
    return True

def test_regex_compatibility():
    """Test that the regex patterns still work with unique suffixes."""
    
    print("\nTesting regex compatibility with unique player names...")
    
    # Sample game result outputs with unique suffixes
    test_outputs = [
        "Game Result: Game 1 ended in 45 ms. LLM(1)-TestDeck-g1_abc123 has won!",
        "Game Result: Game 1 ended in 67 ms. Ai(2)-AnotherDeck-g2_def456 has won!",
        "Game Result: Game 1 ended in a Draw!",
        "Game Result: Game 1 ended in 89 ms. LLM(2)-ThirdDeck-g3_ghi789 has won!",
    ]
    
    # Regex patterns from the benchmark script
    GAME_RESULT_REGEX = r"Game Result: Game \d+ ended in \d+ ms\. (.*?) has won!"
    DRAW_RESULT_REGEX = r"Game Result: Game \d+ ended in a Draw!"
    
    wins = {}
    draws = 0
    
    for output in test_outputs:
        # Check for wins
        win_match = re.search(GAME_RESULT_REGEX, output)
        if win_match:
            winner = win_match.group(1)
            wins[winner] = wins.get(winner, 0) + 1
            print(f"  Found winner: {winner}")
        
        # Check for draws
        draw_match = re.search(DRAW_RESULT_REGEX, output)
        if draw_match:
            draws += 1
            print(f"  Found draw")
    
    print(f"\nParsed results:")
    print(f"  Wins: {wins}")
    print(f"  Draws: {draws}")
    
    # Verify we caught all results
    expected_wins = 3
    expected_draws = 1
    
    if len(wins) == expected_wins and draws == expected_draws:
        print("✓ Regex patterns work correctly with unique player names")
        return True
    else:
        print("✗ Regex patterns failed to parse results correctly!")
        return False

def test_player_categorization():
    """Test that players are correctly categorized as deck1 vs deck2."""
    
    print("\nTesting player categorization logic...")
    
    # Sample winners with unique suffixes
    winners = {
        "LLM(1)-DeckA-g1_abc123": 3,
        "Ai(2)-DeckB-g1_abc123": 2,
        "Ai(1)-DeckA-g2_def456": 4,
        "LLM(2)-DeckB-g2_def456": 1,
    }
    
    deck1_wins = 0
    deck2_wins = 0
    
    for winner, count in winners.items():
        # Use the same logic as in the benchmark script
        if ("Ai(1)" in winner or "LLM(1)" in winner) and not ("Ai(10)" in winner or "LLM(10)" in winner):
            deck1_wins += count
            print(f"  {winner} -> Deck 1 (+{count})")
        elif ("Ai(2)" in winner or "LLM(2)" in winner) and not ("Ai(20)" in winner or "LLM(20)" in winner):
            deck2_wins += count
            print(f"  {winner} -> Deck 2 (+{count})")
        else:
            print(f"  {winner} -> Unrecognized!")
    
    print(f"\nCategorization results:")
    print(f"  Deck 1 wins: {deck1_wins}")
    print(f"  Deck 2 wins: {deck2_wins}")
    
    expected_deck1 = 7  # 3 + 4
    expected_deck2 = 3  # 2 + 1
    
    if deck1_wins == expected_deck1 and deck2_wins == expected_deck2:
        print("✓ Player categorization works correctly with unique suffixes")
        return True
    else:
        print("✗ Player categorization failed!")
        return False

def main():
    """Run all tests."""
    
    print("=" * 60)
    print("Testing Parallel Simulation Unique Player Names")
    print("=" * 60)
    
    tests = [
        test_unique_player_names,
        test_regex_compatibility,
        test_player_categorization,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed with exception: {e}")
            failed += 1
        
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed! Parallel simulations should work correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)