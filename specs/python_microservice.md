Goal: stand up a tiny HTTP server that accepts a JSON‐encoded game state and returns a JSON “move” chosen by your LLM.

Tasks:

    1. Environment & dependencies
       • Create a new folder (e.g. `forge-llm-service/`).
       • Add a `requirements.txt` with at least:
         – flask
         – openai
       • Instruct users to run:

           python3 -m venv venv
           source venv/bin/activate
           pip install -r requirements.txt
           export OPENAI_API_KEY=<your_key>
    2. Define the HTTP server
       • Create `llm_server.py` at the repo root.
       • Import `flask`, `openai`, `json`, `os`.
       • Expose a single endpoint:
         – `POST /act`
         – reads `request.json` (the game‐state blob)
         – returns `application/json`
    3. System prompt & request formatting
       • Hard-code a `SYSTEM_PROMPT` string explaining:
         – You are a Commander AI
         – Input is JSON of battlefield, hand, mana, priorities, etc.
         – Output **must** be JSON `{ action, cardId, spellId, targets[], attackers[]… }`.
       • In the route handler:
         – Combine `SYSTEM_PROMPT` + user message (the raw JSON) into an OpenAI chat completion call.
         – Use `ChatCompletion.create(model="gpt-4", messages=[…], temperature=0.7, max_tokens=200)`.
    4. Response parsing & return
       • Get `.choices[0].message.content` from the API.
       • `json.loads(...)` that content; assume it’s valid JSON.
       • Return `jsonify(parsed_response)` with HTTP 200.
    5. Error handling & logging
       • Catch JSON-decode errors: return HTTP 400 + error message.
       • Catch `openai.error.OpenAIError`: return HTTP 500 + error detail.
       • Print request/response (or write to server log) for debugging.
    6. Configuration & running
       • At bottom of `llm_server.py`, do `app.run(host="0.0.0.0", port=5000)`.
       • Document how to override port or host if needed (via environment or CLI flags).
       • (Optional) Add CORS headers if you ever call it from a browser.
    7. Testing
       • Provide a minimal `curl` example:

           curl -X POST localhost:5000/act -d @sample-state.json -H "Content-Type: application/json"

       • Supply `sample-state.json` with dummy battlefield/hand/phase.