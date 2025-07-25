package forge.view;

import java.io.File;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.apache.commons.lang3.time.StopWatch;

import forge.LobbyPlayer;
import forge.ai.LLMClient;
import forge.ai.LobbyPlayerLLM;
import forge.deck.Deck;
import forge.deck.DeckGroup;
import forge.deck.io.DeckSerializer;
import forge.game.Game;
import forge.game.GameEndReason;
import forge.game.GameLogEntry;
import forge.game.GameLogEntryType;
import forge.game.GameRules;
import forge.game.GameType;
import forge.game.Match;
import forge.game.player.RegisteredPlayer;
import forge.gamemodes.tournament.system.AbstractTournament;
import forge.gamemodes.tournament.system.TournamentBracket;
import forge.gamemodes.tournament.system.TournamentPairing;
import forge.gamemodes.tournament.system.TournamentPlayer;
import forge.gamemodes.tournament.system.TournamentRoundRobin;
import forge.gamemodes.tournament.system.TournamentSwiss;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
import forge.player.GamePlayerUtil;
import forge.util.Lang;
import forge.util.TextUtil;
import forge.util.WordUtil;
import forge.util.storage.IStorage;

public class SimulateMatch {
    public static void simulate(String[] args) {
        System.out.println("=========================================================");
        System.out.println("FORGE SIMULATION MODE STARTING");
        System.out.println("=========================================================");
        
        // Try to catch initialization errors early
        try {
            FModel.initialize(null, null);

        System.out.println("Simulation mode");
        if (args.length < 4) {
            argumentHelp();
            return;
        }

        final Map<String, List<String>> params = new HashMap<>();
        List<String> options = null;

        for (int i = 1; i < args.length; i++) {
            // "sim" is in the 0th slot
            final String a = args[i];

            if (a.charAt(0) == '-') {
                if (a.length() < 2) {
                    System.err.println("Error at argument " + a);
                    argumentHelp();
                    return;
                }

                options = new ArrayList<>();
                params.put(a.substring(1), options);
            } else if (options != null) {
                options.add(a);
            } else {
                System.err.println("Illegal parameter usage");
                return;
            }
        }

        int nGames = 1;
        if (params.containsKey("n")) {
            // Number of games should only be a single string
            nGames = Integer.parseInt(params.get("n").get(0));
        }

        int matchSize = 0;
        if (params.containsKey("m")) {
            // Match size ("best of X games")
            matchSize = Integer.parseInt(params.get("m").get(0));
        }

        boolean outputGamelog = !params.containsKey("q");

        GameType type = GameType.Constructed;
        if (params.containsKey("f")) {
            type = GameType.valueOf(WordUtil.capitalize(params.get("f").get(0)));
        }

        GameRules rules = new GameRules(type);
        rules.setAppliedVariants(EnumSet.of(type));

        if (matchSize != 0) {
            rules.setGamesPerMatch(matchSize);
        }

        if (params.containsKey("t")) {
            simulateTournament(params, rules, outputGamelog);
            System.out.flush();
            return;
        }

        List<RegisteredPlayer> pp = new ArrayList<>();
        StringBuilder sb = new StringBuilder();

        int i = 1;

        if (params.containsKey("d")) {
            for (String deck : params.get("d")) {
                Deck d = deckFromCommandLineParameter(deck, type);
                if (d == null) {
                    System.out.println(TextUtil.concatNoSpace("Could not load deck - ", deck, ", match cannot start"));
                    return;
                }
                if (i > 1) {
                    sb.append(" vs ");
                }
                // Check if controller type is specified
                String controllerType = "ai";
                if (params.containsKey("c")) {
                    List<String> controllers = params.get("c");
                    if (controllers.size() == 1 && controllers.get(0).contains(",")) {
                        // Parse comma-separated list
                        String[] ctrlTypes = controllers.get(0).split(",");
                        if (i - 1 < ctrlTypes.length) {
                            controllerType = ctrlTypes[i - 1].toLowerCase();
                        }
                    } else if (i - 1 < controllers.size()) {
                        controllerType = controllers.get(i - 1).toLowerCase();
                    } else if (!controllers.isEmpty()) {
                        controllerType = controllers.get(0).toLowerCase();
                    }
                }
                
                String name;
                String gameId = System.getProperty("game.id", "");
                String uniqueSuffix = gameId.isEmpty() ? "" : "-" + gameId;
                
                if ("llm".equals(controllerType)) {
                    name = TextUtil.concatNoSpace("LLM(", String.valueOf(i), ")-", d.getName(), uniqueSuffix);
                } else {
                    name = TextUtil.concatNoSpace("Ai(", String.valueOf(i), ")-", d.getName(), uniqueSuffix);
                }
                sb.append(name);

                RegisteredPlayer rp;

                if (type.equals(GameType.Commander)) {
                    rp = RegisteredPlayer.forCommander(d);
                } else {
                    rp = new RegisteredPlayer(d);
                }
                
                // Create appropriate player controller
                LobbyPlayer lobbyPlayer;
                if ("llm".equals(controllerType)) {
                    System.out.println("===============================================");
                    System.out.println("CREATING LLM CONTROLLER FOR PLAYER " + i);
                    System.out.println("===============================================");
                    String llmEndpoint = System.getProperty("llm.endpoint", "http://localhost:7861");
                    System.out.println("Using LLM endpoint: " + llmEndpoint);
                    LLMClient llmClient = new LLMClient(llmEndpoint);
                    lobbyPlayer = new LobbyPlayerLLM(name, llmClient);
                } else {
                    System.out.println("===============================================");
                    System.out.println("CREATING AI CONTROLLER FOR PLAYER " + i);
                    System.out.println("===============================================");
                    lobbyPlayer = GamePlayerUtil.createAiPlayer(name, i - 1);
                }
                
                rp.setPlayer(lobbyPlayer);
                pp.add(rp);
                i++;
            }
        }

        sb.append(" - ").append(Lang.nounWithNumeral(nGames, "game")).append(" of ").append(type);

        System.out.println(sb.toString());

        Match mc = new Match(rules, pp, "Test");

        if (matchSize != 0) {
            int iGame = 0;
            while (!mc.isMatchOver()) {
                // play games until the match ends
                simulateSingleMatch(mc, iGame, outputGamelog);
                iGame++;
            }
        } else {
            for (int iGame = 0; iGame < nGames; iGame++) {
                simulateSingleMatch(mc, iGame, outputGamelog);
            }
        }

        System.out.flush();
        } catch (Exception e) {
            System.err.println("=========================================================");
            System.err.println("CRITICAL INITIALIZATION ERROR");
            System.err.println("=========================================================");
            e.printStackTrace();
            System.err.println("=========================================================");
            System.exit(1);
        }
    }

    private static void argumentHelp() {
        System.out.println("Syntax: forge.exe sim -d <deck1[.dck]> ... <deckX[.dck]> -D [D] -n [N] -m [M] -t [T] -p [P] -f [F] -c [C] -q");
        System.out.println("\tsim - stands for simulation mode");
        System.out.println("\tdeck1 (or deck2,...,X) - constructed deck name or filename (has to be quoted when contains multiple words)");
        System.out.println("\tdeck is treated as file if it ends with a dot followed by three numbers or letters");
        System.out.println("\tBigQuery deck IDs (containing hyphens) will be automatically downloaded if not found locally");
        System.out.println("\tD - absolute directory to load decks from");
        System.out.println("\tN - number of games, defaults to 1 (Ignores match setting)");
        System.out.println("\tM - Play full match of X games, typically 1,3,5 games. (Optional, overrides N)");
        System.out.println("\tT - Type of tournament to run with all provided decks (Bracket, RoundRobin, Swiss)");
        System.out.println("\tP - Amount of players per match (used only with Tournaments, defaults to 2)");
        System.out.println("\tF - format of games, defaults to constructed");
        System.out.println("\tC - controller type for players (llm, ai, or comma-separated list like 'llm,ai')");
        System.out.println("\tq - Quiet flag. Output just the game result, not the entire game log.");
        System.out.println();
        System.out.println("BigQuery Deck Download:");
        System.out.println("\tDecks with hyphens in their names are automatically detected as BigQuery deck IDs");
        System.out.println("\tExample: 'commander-deck-12345' will be downloaded from BigQuery before simulation");
        System.out.println("\tRequires Python simulation service running on localhost:5000 with BigQuery credentials");
        System.out.println("\tFalls back to get_decks.py script if HTTP service is unavailable");
    }

    public static void simulateSingleMatch(final Match mc, int iGame, boolean outputGamelog) {
        String gameId = System.getProperty("game.id", "unknown");
        System.out.println("DEBUG: Starting simulateSingleMatch for game " + gameId);
        
        final StopWatch sw = new StopWatch();
        sw.start();

        final Game g1 = mc.createGame();
        System.out.println("DEBUG: Game created for " + gameId);
        
        // will run match in the same thread
        try {
            System.out.println("DEBUG: Starting game execution for " + gameId);
            TimeLimitedCodeBlock.runWithTimeout(() -> {
                mc.startGame(g1);
                sw.stop();
                System.out.println("DEBUG: Game execution completed for " + gameId);
            }, 1200, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            System.out.println("DEBUG: Game " + gameId + " timed out, stopping as draw");
            System.out.println("Stopping slow match as draw");
        } catch (Exception | StackOverflowError e) {
            System.err.println("============================================================");
            System.err.println("CRITICAL ERROR DURING SIMULATION (Game " + gameId + ")");
            System.err.println("============================================================");
            e.printStackTrace();
            System.err.println("============================================================");
            System.err.println("Terminating simulation due to critical error");
            System.err.println("============================================================");
            System.exit(1);  // Terminate process on critical errors
        } finally {
            if (sw.isStarted()) {
                sw.stop();
            }
            if (!g1.isGameOver()) {
                g1.setGameOver(GameEndReason.Draw);
            }
            System.out.println("DEBUG: simulateSingleMatch cleanup completed for " + gameId);
        }

        List<GameLogEntry> log;
        if (outputGamelog) {
            log = g1.getGameLog().getLogEntries(null);
        } else {
            log = g1.getGameLog().getLogEntries(GameLogEntryType.MATCH_RESULTS);
        }
        Collections.reverse(log);
        for (GameLogEntry l : log) {
            System.out.println(l);
        }

        // If both players life totals to 0 in a single turn, the game should end in a draw
        if (g1.getOutcome().isDraw()) {
            System.out.printf("\nGame Result: Game %d ended in a Draw! Took %d ms.%n", 1 + iGame, sw.getTime());
        } else {
            System.out.printf("\nGame Result: Game %d ended in %d ms. %s has won!\n%n", 1 + iGame, sw.getTime(), g1.getOutcome().getWinningLobbyPlayer().getName());
        }
    }

    private static void simulateTournament(Map<String, List<String>> params, GameRules rules, boolean outputGamelog) {
        String tournament = params.get("t").get(0);
        AbstractTournament tourney = null;
        int matchPlayers = params.containsKey("p") ? Integer.parseInt(params.get("p").get(0)) : 2;

        DeckGroup deckGroup = new DeckGroup("SimulatedTournament");
        List<TournamentPlayer> players = new ArrayList<>();
        int numPlayers = 0;
        if (params.containsKey("d")) {
            for (String deck : params.get("d")) {
                Deck d = deckFromCommandLineParameter(deck, rules.getGameType());
                if (d == null) {
                    System.out.println(TextUtil.concatNoSpace("Could not load deck - ", deck, ", match cannot start"));
                    return;
                }

                deckGroup.addAiDeck(d);
                
                // Check if controller type is specified
                String controllerType = "ai";
                if (params.containsKey("c")) {
                    List<String> controllers = params.get("c");
                    if (controllers.size() == 1 && controllers.get(0).contains(",")) {
                        // Parse comma-separated list
                        String[] ctrlTypes = controllers.get(0).split(",");
                        if (numPlayers < ctrlTypes.length) {
                            controllerType = ctrlTypes[numPlayers].toLowerCase();
                        }
                    } else if (numPlayers < controllers.size()) {
                        controllerType = controllers.get(numPlayers).toLowerCase();
                    } else if (!controllers.isEmpty()) {
                        controllerType = controllers.get(0).toLowerCase();
                    }
                }
                
                LobbyPlayer lobbyPlayer;
                String gameId = System.getProperty("game.id", "");
                String uniqueSuffix = gameId.isEmpty() ? "" : "-" + gameId;
                String playerName = d.getName() + uniqueSuffix;
                
                if ("llm".equals(controllerType)) {
                    String llmEndpoint = System.getProperty("llm.endpoint", "http://localhost:7861");
                    if (numPlayers == 0) { // Only print once
                        System.out.println("Using LLM endpoint: " + llmEndpoint);
                    }
                    LLMClient llmClient = new LLMClient(llmEndpoint);
                    lobbyPlayer = new LobbyPlayerLLM(playerName, llmClient);
                } else {
                    lobbyPlayer = GamePlayerUtil.createAiPlayer(playerName, 0);
                }
                
                players.add(new TournamentPlayer(lobbyPlayer, numPlayers));
                numPlayers++;
            }
        }

        if (params.containsKey("D")) {
            // Direc
            String foldName = params.get("D").get(0);
            File folder = new File(foldName);
            if (!folder.isDirectory()) {
                System.out.println("Directory not found - " + foldName);
            } else {
                for (File deck : folder.listFiles((dir, name) -> name.endsWith(".dck"))) {
                    Deck d = DeckSerializer.fromFile(deck);
                    if (d == null) {
                        System.out.println(TextUtil.concatNoSpace("Could not load deck - ", deck.getName(), ", match cannot start"));
                        return;
                    }
                    deckGroup.addAiDeck(d);
                    
                    // Check if controller type is specified
                    String controllerType = "ai";
                    if (params.containsKey("c")) {
                        List<String> controllers = params.get("c");
                        if (controllers.size() == 1 && controllers.get(0).contains(",")) {
                            // Parse comma-separated list
                            String[] ctrlTypes = controllers.get(0).split(",");
                            if (numPlayers < ctrlTypes.length) {
                                controllerType = ctrlTypes[numPlayers].toLowerCase();
                            }
                        } else if (numPlayers < controllers.size()) {
                            controllerType = controllers.get(numPlayers).toLowerCase();
                        } else if (!controllers.isEmpty()) {
                            controllerType = controllers.get(0).toLowerCase();
                        }
                    }
                    
                    LobbyPlayer lobbyPlayer;
                    String gameId = System.getProperty("game.id", "");
                    String uniqueSuffix = gameId.isEmpty() ? "" : "-" + gameId;
                    String playerName = d.getName() + uniqueSuffix;
                    
                    if ("llm".equals(controllerType)) {
                        String llmEndpoint = System.getProperty("llm.endpoint", "http://localhost:7861");
                        LLMClient llmClient = new LLMClient(llmEndpoint);
                        lobbyPlayer = new LobbyPlayerLLM(playerName, llmClient);
                    } else {
                        lobbyPlayer = GamePlayerUtil.createAiPlayer(playerName, 0);
                    }
                    
                    players.add(new TournamentPlayer(lobbyPlayer, numPlayers));
                    numPlayers++;
                }
            }

        }

        if (numPlayers == 0) {
            System.out.println("No decks/Players found. Please try again.");
        }

        if ("bracket".equalsIgnoreCase(tournament)) {
            tourney = new TournamentBracket(players, matchPlayers);
        } else if ("roundrobin".equalsIgnoreCase(tournament)) {
            tourney = new TournamentRoundRobin(players, matchPlayers);
        } else if ("swiss".equalsIgnoreCase(tournament)) {
            tourney = new TournamentSwiss(players, matchPlayers);
        }
        if (tourney == null) {
            System.out.println("Failed to initialize tournament, bailing out");
            return;
        }

        tourney.initializeTournament();

        String lastWinner = "";
        int curRound = 0;
        System.out.println(TextUtil.concatNoSpace("Starting a ", tournament, " tournament with ",
                String.valueOf(numPlayers), " players over ",
                String.valueOf(tourney.getTotalRounds()), " rounds"));
        while (!tourney.isTournamentOver()) {
            if (tourney.getActiveRound() != curRound) {
                if (curRound != 0) {
                    System.out.println(TextUtil.concatNoSpace("End Round - ", String.valueOf(curRound)));
                }
                curRound = tourney.getActiveRound();
                System.out.println();
                System.out.println(TextUtil.concatNoSpace("Round ", String.valueOf(curRound), " Pairings:"));

                for (TournamentPairing pairing : tourney.getActivePairings()) {
                    System.out.println(pairing.outputHeader());
                }
                System.out.println();
            }

            TournamentPairing pairing = tourney.getNextPairing();
            List<RegisteredPlayer> regPlayers = AbstractTournament.registerTournamentPlayers(pairing, deckGroup);

            StringBuilder sb = new StringBuilder();
            sb.append("Round ").append(tourney.getActiveRound()).append(" - ");
            sb.append(pairing.outputHeader());
            System.out.println(sb.toString());

            if (!pairing.isBye()) {
                Match mc = new Match(rules, regPlayers, "TourneyMatch");

                int exceptions = 0;
                int iGame = 0;
                while (!mc.isMatchOver()) {
                    // play games until the match ends
                    try {
                        simulateSingleMatch(mc, iGame, outputGamelog);
                        iGame++;
                    } catch (Exception e) {
                        exceptions++;
                        System.out.println(e.toString());
                        if (exceptions > 5) {
                            System.out.println("Exceeded number of exceptions thrown. Abandoning match...");
                            break;
                        } else {
                            System.out.println("Game threw exception. Abandoning game and continuing...");
                        }
                    }

                }
                LobbyPlayer winner = mc.getWinner().getPlayer();
                for (TournamentPlayer tp : pairing.getPairedPlayers()) {
                    if (winner.equals(tp.getPlayer())) {
                        pairing.setWinner(tp);
                        lastWinner = winner.getName();
                        System.out.println(TextUtil.concatNoSpace("Match Winner - ", lastWinner, "!"));
                        System.out.println();
                        break;
                    }
                }
            }

            tourney.reportMatchCompletion(pairing);
        }
        tourney.outputTournamentResults();
    }

    public static Match simulateOffthreadGame(List<Deck> decks, GameType format, int games) {
        return null;
    }

    private static Deck deckFromCommandLineParameter(String deckname, GameType type) {
        // Check if this looks like a BigQuery deck ID
        if (DeckDownloader.isBigQueryDeckId(deckname)) {
            String gameTypeName = type.equals(GameType.Commander) ? "Commander" : "Constructed";
            
            // NOTE: Deck downloading should be handled by the Python simulation service
            // before the Java simulation starts. Java will only load locally available decks.
            System.out.println("BigQuery deck ID detected: " + deckname);
            
            // Try to find the deck file using the exact deck ID (saved by Python service)
            String baseDir = type.equals(GameType.Commander) ?
                    ForgeConstants.DECK_COMMANDER_DIR : ForgeConstants.DECK_CONSTRUCTED_DIR;
            
            // First try exact deck ID as filename
            File deckFile = new File(baseDir, deckname + ".dck");
            if (deckFile.exists()) {
                System.out.println("Loading deck from: " + deckFile.getAbsolutePath());
                return DeckSerializer.fromFile(deckFile);
            }
            
            // Try sanitized version of deck ID as filename
            String sanitizedDeckName = DeckDownloader.sanitizeFilename(deckname);
            File sanitizedDeckFile = new File(baseDir, sanitizedDeckName + ".dck");
            if (sanitizedDeckFile.exists()) {
                System.out.println("Loading deck from: " + sanitizedDeckFile.getAbsolutePath());
                return DeckSerializer.fromFile(sanitizedDeckFile);
            }
            
            System.err.println("Could not find deck file for BigQuery ID: " + deckname + 
                             " (checked: " + deckFile.getName() + ", " + sanitizedDeckFile.getName() + ")");
        }
        
        int dotpos = deckname.lastIndexOf('.');
        if (dotpos > 0 && dotpos == deckname.length() - 4) {
            String baseDir = type.equals(GameType.Commander) ?
                    ForgeConstants.DECK_COMMANDER_DIR : ForgeConstants.DECK_CONSTRUCTED_DIR;

            File f = new File(baseDir + deckname);
            if (!f.exists()) {
                System.out.println("No deck found in " + baseDir);
            }

            return DeckSerializer.fromFile(f);
        }

        IStorage<Deck> deckStore = null;

        // Add other game types here...
        if (type.equals(GameType.Commander)) {
            deckStore = FModel.getDecks().getCommander();
        } else {
            deckStore = FModel.getDecks().getConstructed();
        }

        return deckStore.get(deckname);
    }

}