Goal: let forge … sim attach LobbyPlayerLLM instead of LobbyPlayerAi when the user requests -c llm.

Tasks:

    1. Add new CLI option parsing
       • In `forge-gui-desktop/src/main/java/forge/view/SimulateMatch.java`, locate the code block that builds `params` from args.
       • After you pull `params`, detect if `params.containsKey("c")`.
       • Read `String controllerType = params.get("c").get(0).toLowerCase();`
       • Define `boolean useLLM = "llm".equals(controllerType);`
    2. Read the LLM endpoint
       • Immediately after, read:

           String llmEndpoint = System.getProperty("llm.endpoint", "http://localhost:5000");
           LLMClient llmClient = useLLM ? new LLMClient(llmEndpoint) : null;

       • Make sure you import your `forge.ai.LLMClient`.
    3. Swap player‐factory in deck loop
       In the loop that does:

           RegisteredPlayer rp = type==Commander
                                  ? RegisteredPlayer.forCommander(d)
                                  : new RegisteredPlayer(d);
           rp.setPlayer(GamePlayerUtil.createAiPlayer(...));

       Replace the `setPlayer(...)` line with:

           if (useLLM) {
               rp.setPlayer(new LobbyPlayerLLM(name, llmClient));
           } else {
               rp.setPlayer(GamePlayerUtil.createAiPlayer(name, i-1));
           }
    4. Imports & wiring
       • Import `forge.ai.LobbyPlayerLLM`.
       • Import `forge.ai.LLMClient`.
       • Ensure the `RegisteredPlayer` uses `forCommander(d)` when `GameType.Commander` is set.
    5. Build & packaging
       • Run `mvn package -pl forge-ai,forge-gui-desktop`.
       • Confirm `forge-gui-desktop-…jar-with-dependencies.jar` includes your new AI classes.
    6. Usage & validation
       • Document the full command:

           java -Xmx4g \
             -Dllm.endpoint=http://localhost:5000 \
             -jar forge-gui-desktop-<ver>-jar-with-dependencies.jar \
             sim -f Commander \
             -d Deck1.dck Deck2.dck ... -c llm -n 10

       • Run a quick 1-game sim and verify in the logs that HTTP calls are fired to your Python service and that moves appear in the game log.
    7. Fallback & CLI help
       • If `-c` is missing or not recognized, default back to AI.
       • Update any usage/help text in `argumentHelp()` to mention `-c llm`.