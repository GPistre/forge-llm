Goal: from within Forge’s Java code, send the serialized game‐state JSON to your Flask service and retrieve its JSON move.

Tasks:

    1. Add JSON library
       • In `forge-ai/pom.xml`, add a dependency on `com.google.code.gson:gson:2.x`.
    2. Create `LLMClient` class
       • Path: `forge-ai/src/main/java/forge/ai/LLMClient.java`.
       • Package: `forge.ai`.
       • Fields:
         – `private final String endpoint;`
         – `private final Gson gson = new Gson();`
    3. Constructor
       • `public LLMClient(String endpointUrl)` that sets `this.endpoint = endpointUrl;`.
    4. Core method `ask(JsonObject gameState)`
       • Signature:

           public JsonObject ask(JsonObject gameState) throws IOException;

       • Inside:
         – Create `URL url = new URL(endpoint + "/act");`
         – `HttpURLConnection conn = (HttpURLConnection) url.openConnection();`
         – `conn.setRequestMethod("POST");`
         – `conn.setDoOutput(true);`
         – `conn.setRequestProperty("Content-Type", "application/json; utf-8");`
         – Write `gson.toJson(gameState)` to `conn.getOutputStream()`.
         – Read response code: if not 200, throw IOException with `conn.getResponseMessage()`.
         – Else read `conn.getInputStream()` into a `JsonObject` via `gson.fromJson(reader, JsonObject.class)`.
         – Return that JsonObject.
    5. Timeouts & resource cleanup
       • Optionally call `conn.setConnectTimeout(...)` and `conn.setReadTimeout(...)` (e.g. 30 s).
       • Ensure streams are closed with try‐with‐resources.
    6. Error propagation
       • Let IOExceptions bubble up for the caller to handle.
       • Document in Javadoc that network or parse errors may be thrown.
    7. Unit test stub (optional)
       • Add a simple JUnit test that starts a dummy HTTP server returning a known JSON and verifies `ask()` returns it.