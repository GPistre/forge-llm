# CLAUDE.md
ALWAYS use the /Users/geromepistre/miniconda3/envs/forge4/bin/python interpreter and associated pip
ALWAYS use the bigquery / GCP credentials in simulation-app/.env
When testing, use the deck id `moxfield-TdOsPBP3302BdskyLVzU-A`

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Forge is an open-source Magic: The Gathering rules engine and game client implemented in Java. It provides a dynamic and cross-platform experience for playing MTG against AI or other players, with support for various game modes including Adventure Mode, Quest Modes, and different AI formats.

## Build System

The project uses Maven for build management:

```bash
# Build the entire project (Windows/Linux)
mvn -U -B clean -P windows-linux install

# Build specific modules
mvn package -pl forge-ai,forge-gui-desktop

# Run tests
mvn test
```

## Running the Project

### Desktop Version

To run the desktop version:

```bash
# From the command line after building
cd forge-gui-desktop/target/forge-gui-desktop-[version]-SNAPSHOT
java -jar forge-gui-desktop-[version]-SNAPSHOT.jar
```

### Mobile Development Version

To run the mobile development version:

```bash
# From the command line after building
cd forge-gui-mobile-dev/target
java -jar forge-gui-mobile-dev-[version]-SNAPSHOT.jar
```

## Project Structure

The codebase is organized into several modules:

- **forge-core**: Core utilities and basic functionality
- **forge-game**: Game logic and rules implementation 
- **forge-ai**: AI player implementation
- **forge-gui**: Game UI elements shared across platforms
- **Platform-specific implementations**:
  - **forge-gui-desktop**: Swing-based desktop client
  - **forge-gui-mobile**: Mobile UI logic using libgdx
  - **forge-gui-android**: Android implementation
  - **forge-gui-ios**: iOS implementation
  - **forge-gui-mobile-dev**: Development tools for mobile
- **Additional modules**:
  - **forge-lda**: Card analysis/recommendations
  - **adventure-editor**: Editor for the Adventure mode
  - **forge-installer**: Installation packaging

## Card Scripting

Card scripting resources are found in the `forge-gui/res/` path. The project includes extensive resources for cards, editions, and game modes.

## Work In Progress Features

The project is actively developing several new features:
- LLM (Large Language Model) integration for AI (see `specs/llm_client.md`)
- Player controller improvements (see `specs/player_controller.md`)
- Python microservice integration (see `specs/python_microservice.md`)
- Match simulation improvements (see `specs/simulate_match.md`)

## LLM Integration

### Testing Instructions

1. Start the LLM service:
   ```bash
   cd forge-llm-service
   python3 test_server.py
   ```

2. Run the test script:
   ```bash
   ./run_llm_test.sh
   ```

3. Test API communication directly:
   ```bash
   curl -s -X POST -H "Content-Type: application/json" -d '{"context":"debug","message":"test"}' http://localhost:7861/act
   ```

### Implementation Notes

- `LLMClient.java` - HTTP client for communicating with the LLM service
- `LobbyPlayerLLM.java` - LLM player representation in the game lobby
- `PlayerControllerLLM.java` - Core gameplay decision-making implementation
- `SimulateMatch.java` - Modified to support LLM controller via `-c llm` parameter
- `test_server.py` - Simple Flask server for testing the integration

### Troubleshooting

1. If you encounter an "Address already in use" error, change the port in `test_server.py` and update the `llm.endpoint` property accordingly.

2. If you get an ExceptionInInitializerError when running sim commands, this is a known issue with the Forge initialization in headless mode. However, the LLM communication itself works, as can be verified by:
   - Running the curl test command above
   - Running the test script which verifies API connectivity

3. To avoid initialization issues in sim mode, we've implemented robust error handling in LLMClient that allows it to gracefully handle errors and provide fallback responses.

## Requirements

- Java JDK 17 or later
- Maven 3.8.1 or later
- Git

For the simulation app:
- Python 3.x with conda environment: `/Users/geromepistre/miniconda3/envs/forge4/bin/python`
- Flask and related dependencies (see simulation-app/requirements.txt)

For mobile development:
- Libgdx
- Android SDK (for Android)
- RoboVM (for iOS)

## Code Quality

The project uses checkstyle for code quality. The checkstyle configuration is defined in `checkstyle.xml` and is enforced during the build process.