# Forge LLM Microservice

This is a Python Flask microservice that enables Forge to use an LLM (Large Language Model) for game decisions instead of the traditional AI. It includes multiple components:

- `test_server.py`: The main server with OpenAI integration, error handling, and logging
- `llm_client.py`: A dedicated client library for LLM interactions
- `test_client.py`: A test client for validating the server functionality

## Setup

1. Create a Python virtual environment:
```
python3 -m venv venv
```

2. Activate the virtual environment:
```
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. Install the required dependencies:
```
pip install -r requirements.txt
```

4. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Running the Service

You can run either server implementation:

### Original Server
```
python llm_server.py
```
By default, the server runs on port 7860.

### Enhanced Test Server
```
python test_server.py
```
By default, the test server runs on port 7861.

You can change the port for either server by setting the `PORT` environment variable.

## Testing

You can test the service using curl:

### Original Server
```
curl -X POST http://localhost:7860/act -H "Content-Type: application/json" -d @sample-state.json
```

### Enhanced Test Server
```
curl -X POST http://localhost:7861/act -H "Content-Type: application/json" -d @sample-state.json
```

The test server also supports special test contexts:

```json
{"context": "testing"}
```
Returns a test response message.

```json
{"context": "debug"}
```
Returns a simple PASS action.

## Using with Forge

To use this service with Forge, run Forge with the `-c llm` parameter and specify the appropriate endpoint:

### With Original Server
```
java -Xmx4g -Dllm.endpoint=http://localhost:7860 -jar forge-gui-desktop-<version>-jar-with-dependencies.jar sim -f Commander -d <deck1.dck> <deck2.dck> -c llm -n 1
```

### With Enhanced Test Server
```
java -Xmx4g -Dllm.endpoint=http://localhost:7861 -jar forge-gui-desktop-<version>-jar-with-dependencies.jar sim -f Commander -d <deck1.dck> <deck2.dck> -c llm -n 1
```

## Response Format

The LLM will return JSON responses based on the context:

- For ability selection:
```json
{
  "action": "ACTIVATE",
  "spellAbilityId": "ability-id"
}
```

- For target selection:
```json
{
  "targets": ["card-id-1", "card-id-2"]
}
```

- For declaring attackers:
```json
{
  "attackers": [
    {"cardId": "attacker-id", "defenderId": "defender-id"}
  ]
}
```

And similar formats for other game actions.

## Enhanced Test Server Features

- Improved error handling with detailed error messages
- Comprehensive logging to both console and file (flask_server.log)
- Fallback responses when the OpenAI API fails
- Special test and debug endpoints
- Extraction of valid JSON from malformed LLM responses
- Custom default responses based on game context