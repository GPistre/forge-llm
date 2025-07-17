Goal: extend Forge’s PlayerController so every decision is fetched via your LLMClient.

Tasks:

    1. New factory class `LobbyPlayerLLM`
       • Path: `forge-ai/src/main/java/forge/ai/LobbyPlayerLLM.java`.
       • Package: `forge.ai`.
       • Subclass `extends LobbyPlayer implements IGameEntitiesFactory`.
       • Add a field `private final LLMClient client;`
       • Constructor takes `(String name, LLMClient client)`.
       • `createIngamePlayer(Game g, int id)`:
         – Instantiate new `Player(name, g, id)`.
         – Attach `p.setFirstController(new PlayerControllerLLM(g, p, this, client))`.
         – Return `p`.
       • `createMindSlaveController(...)`: same controller creation for slave.
       • `hear(...)`: no‐op.
    2. New controller class `PlayerControllerLLM`
       • Path: `forge-ai/src/main/java/forge/ai/PlayerControllerLLM.java`.
       • Package: `forge.ai`.
       • Subclass `extends PlayerController`.
       • Fields:
         – `private final LLMClient client;`
       • Constructor `(Game g, Player p, LobbyPlayer lp, LLMClient client)` → `super(g,p,lp)` + store client.
    3. Implement abstract methods
       For each of the methods in `PlayerController` marked `abstract`, do:
       a) Serialize current choice context into a `JsonObject state`.


        * e.g. for `getAbilityToPlay(Card host, List<SpellAbility> abs, ITriggerEvent ev)`:
             • Build JSON with: host card id, list of `abs` ids + text, game‐phase, your mana, commanders, battlefield etc.
             b) Call `JsonObject reply = client.ask(state);` (catch `IOException`, fallback to “pass” or call super).
             c) Parse `reply` fields:
               – `"action": "CAST"` or `"PASS"` → map to specific API call.
               – `"spellAbilityId"` or `"cardId"` → find matching `SpellAbility` in the provided list.
               – `"targets": [ id, … ]` → look up game objects via `game.getCardById()`.
             d) Return the appropriate object (`SpellAbility`, `boolean`, `CardCollection`, `List<Card>`, etc.) per the method signature.
    4. Minimum viable subset
       At first, only implement the most‐used methods:
       – `getAbilityToPlay(...)`
       – `chooseTargetsFor(...)`
       – `declareAttackers(...)`, `declareBlockers(...)`
       – `confirmAction(...)` (yes/no)
       – `chooseSingleEntityForEffect(...)` / `chooseEntitiesForEffect(...)`
       All remaining methods can default to passing priority or “no choice” until you expand.
    5. Helper utilities
       • You may want a `JsonUtil` class to turn `List<SpellAbility>` into JSON arrays and back.
       • Standardize on “id” fields across all JSON blobs for lookup.
    6. Error/fallback behavior
       • On any JSON parse or network error, log a warning and fall back to `PlayerControllerAi` (or “pass priority”).
       • Make sure illegal moves (LLM suggests invalid ids) are caught—reject and send a new prompt, or default to pass.
    7. Testing
       • Create a small `Game` + single `RegisteredPlayer` deck vs. a dumb AI.
       • Verify your LLM‐bot actually calls out to the Python server and returns a non‐null decision.