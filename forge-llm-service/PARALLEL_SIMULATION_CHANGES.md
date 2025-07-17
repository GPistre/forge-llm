# Parallel Simulation Changes - Player Name Conflict Fix

## Problem
When running multiple Forge simulations in parallel, all games would create players with the same names (e.g., "LLM(1)", "LLM(2)"), potentially causing conflicts in the LLM server if it tracks players by name.

## Solution
Implemented automatic generation of unique player identifiers for each parallel game simulation.

## Changes Made

### 1. Python Script Changes (`run_benchmark.py`)

#### Added UUID Generation
- Added `import uuid` for unique ID generation
- Each parallel game now gets a unique 8-character identifier

#### Modified Function Signatures
- `run_single_game()` now accepts both `game_id` (for logging) and `unique_id` (for Java)
- `run_simulation()` now accepts `game_id` parameter

#### Enhanced Task Creation
```python
# Before
game_id = f"{config['name']}_game_{i+1}"

# After  
short_uuid = str(uuid.uuid4())[:8]
game_id = f"{config['name']}_game_{i+1}_{short_uuid}"
unique_id = f"g{i+1}_{short_uuid}"
```

#### Updated Java Command Generation
- Added `-Dgame.id=<unique_id>` system property to Java commands
- Short unique IDs passed to avoid overly long player names

#### Improved Result Parsing
- Updated regex logic to handle player names with unique suffixes
- Enhanced categorization logic to avoid false matches (e.g., "Ai(10)" vs "Ai(1)")

### 2. Java Changes (`SimulateMatch.java`)

#### Player Name Generation
```java
// Before
name = TextUtil.concatNoSpace("LLM(", String.valueOf(i), ")-", d.getName());

// After
String gameId = System.getProperty("game.id", "");
String uniqueSuffix = gameId.isEmpty() ? "" : "-" + gameId;
name = TextUtil.concatNoSpace("LLM(", String.valueOf(i), ")-", d.getName(), uniqueSuffix);
```

#### Updated All Player Creation Points
- Main simulation loop
- Tournament simulation (deck parameter)
- Tournament simulation (directory parameter)

### 3. Test Script (`test_parallel_unique_names.py`)

Created comprehensive test script to verify:
- Unique ID generation works correctly
- Regex patterns still parse results with suffixes
- Player categorization logic handles unique names
- No conflicts between parallel games

## Example Player Names

### Before (Conflict Prone)
```
Game 1: LLM(1)-DeckA, LLM(2)-DeckB
Game 2: LLM(1)-DeckA, LLM(2)-DeckB  // Same names!
Game 3: LLM(1)-DeckA, LLM(2)-DeckB  // Same names!
```

### After (Unique)
```
Game 1: LLM(1)-DeckA-g1_8a1f2cc0, LLM(2)-DeckB-g1_8a1f2cc0
Game 2: LLM(1)-DeckA-g2_55dddbc0, LLM(2)-DeckB-g2_55dddbc0
Game 3: LLM(1)-DeckA-g3_a9b4332a, LLM(2)-DeckB-g3_a9b4332a
```

## Benefits

1. **No LLM Server Conflicts**: Each parallel game has unique player names
2. **Backwards Compatibility**: Works with existing single-game simulations
3. **Automatic**: No manual configuration needed
4. **Short Suffixes**: Uses 8-character UUIDs to keep names manageable
5. **Robust Parsing**: Result analysis still works correctly

## Testing

Run the test script to verify functionality:
```bash
cd forge-llm-service
python3 test_parallel_unique_names.py
```

Expected output: All tests should pass with ✓ marks.

## Usage

The changes are automatic and transparent. Simply use the parallel benchmark as before:

```bash
python3 run_benchmark.py deck1.dck deck2.dck -n 20 -w 4
```

Each of the 20 games will now have unique player names, preventing any conflicts in the LLM service.

## Files Modified

1. `forge-llm-service/run_benchmark.py` - Main parallel simulation logic
2. `forge-gui-desktop/src/main/java/forge/view/SimulateMatch.java` - Player name generation
3. `forge-llm-service/README-PARALLEL-BENCHMARKING.md` - Updated documentation
4. `forge-llm-service/test_parallel_unique_names.py` - New test script (created)
5. `forge-llm-service/PARALLEL_SIMULATION_CHANGES.md` - This file (created)

## Performance Impact

Minimal impact:
- UUID generation is fast (microseconds)
- Slightly longer player names (8 extra characters)
- No change to simulation speed or memory usage
- Network calls to LLM service now have unique player identifiers