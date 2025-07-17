package forge.view;

import com.google.gson.JsonObject;
import forge.LobbyPlayer;
import forge.ai.LLMClient;
import forge.ai.LobbyPlayerLLM;
import forge.deck.Deck;
import forge.deck.io.DeckSerializer;
import forge.game.Game;
import forge.game.GameRules;
import forge.game.GameType;
import forge.game.Match;
import forge.game.phase.PhaseType;
import forge.game.player.RegisteredPlayer;
import forge.game.zone.ZoneType;
// import forge.localinstance.properties.ForgeConstants; // Can't use due to initialization issues
import forge.player.GamePlayerUtil;
import forge.util.FileUtil;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * Simple test class for simulating a game with an LLM controller.
 * Minimal implementation with minimal dependencies.
 */
public class TestSimpleGame {

    public static void main(String[] args) {
        try {
            System.out.println("Starting Simple Game Test");
            
            // We can't use ForgeConstants directly due to initialization issues
            // Instead, we'll use absolute paths for this test
            String userDir = System.getProperty("user.home") + "/Forge";
            FileUtil.ensureDirectoryExists(userDir);
            FileUtil.ensureDirectoryExists(userDir + "/cache");
            FileUtil.ensureDirectoryExists(userDir + "/games");
            FileUtil.ensureDirectoryExists(userDir + "/decks/constructed");
            FileUtil.ensureDirectoryExists(userDir + "/decks/commander");
            
            // Set up LLM client
            String llmEndpoint = System.getProperty("llm.endpoint", "http://localhost:7861");
            System.out.println("Using LLM endpoint: " + llmEndpoint);
            LLMClient llmClient = new LLMClient(llmEndpoint);
            
            // Test basic request
            JsonObject testObj = new JsonObject();
            testObj.addProperty("context", "debug");
            testObj.addProperty("message", "Simple test from TestSimpleGame");
            
            System.out.println("Sending test request to LLM service...");
            try {
                JsonObject response = llmClient.ask(testObj);
                System.out.println("Response from LLM service: " + response);
                System.out.println("LLM service communication successful!");
            } catch (Exception e) {
                System.err.println("Error communicating with LLM service: " + e.getMessage());
                e.printStackTrace();
                return;
            }
            
            // Parse command line args
            String deckPath1 = args.length > 0 ? args[0] : "/Users/gpistre/perso/forge4/decks/commander/2729356-magus-lucea-kane.dck";
            String deckPath2 = args.length > 1 ? args[1] : "/Users/gpistre/perso/forge4/decks/commander/2397321-kathril-aspect-warper-invincib.dck";
            
            // Load decks
            Deck deck1 = loadDeck(deckPath1);
            if (deck1 == null) {
                System.out.println("Failed to load first deck: " + deckPath1);
                return;
            }
            
            Deck deck2 = loadDeck(deckPath2);
            if (deck2 == null) {
                System.out.println("Failed to load second deck: " + deckPath2);
                return;
            }
            
            System.out.println("Loaded decks: " + deck1.getName() + " vs " + deck2.getName());
            
            // Create players
            List<RegisteredPlayer> players = new ArrayList<>();
            
            // LLM player
            String llmPlayerName = "LLM-" + deck1.getName().substring(0, Math.min(deck1.getName().length(), 15));
            LobbyPlayer llmPlayer = new LobbyPlayerLLM(llmPlayerName, llmClient);
            RegisteredPlayer rp1 = new RegisteredPlayer(deck1);
            rp1.setPlayer(llmPlayer);
            players.add(rp1);
            
            // AI player
            String aiPlayerName = "AI-" + deck2.getName().substring(0, Math.min(deck2.getName().length(), 15));
            LobbyPlayer aiPlayer = GamePlayerUtil.createAiPlayer(aiPlayerName, 0);
            RegisteredPlayer rp2 = new RegisteredPlayer(deck2);
            rp2.setPlayer(aiPlayer);
            players.add(rp2);
            
            // Set up game rules
            GameRules rules = new GameRules(GameType.Constructed);
            
            // Create match
            System.out.println("Creating match");
            Match match = new Match(rules, players, "Simple Test Match");
            
            // Create and start game
            Game game = match.createGame();
            System.out.println("Starting game");
            
            try {
                match.startGame(game);
                System.out.println("Game started successfully");
                
                // Let the game run for a bit
                while (!game.isGameOver() && game.getPhaseHandler().getTurn() < 5) {
                    Thread.sleep(500);
                    System.out.println("Turn " + game.getPhaseHandler().getTurn() + 
                                      ", Phase: " + game.getPhaseHandler().getPhase());
                    
                    // Print active player's hand
                    if (game.getPhaseHandler().getPhase() == PhaseType.MAIN1) {
                        int handSize = game.getPhaseHandler().getPlayerTurn().getCardsIn(ZoneType.Hand).size();
                        System.out.println("Active player has " + handSize + " cards in hand");
                    }
                }
                
                if (game.isGameOver()) {
                    System.out.println("Game ended: " + game.getOutcome().toString());
                } else {
                    System.out.println("Game stopped after 5 turns");
                    // Force game to end without calling endGame directly
                    game.setGameOver(forge.game.GameEndReason.Draw);
                }
                
            } catch (Exception e) {
                System.err.println("Error during game: " + e.getMessage());
                e.printStackTrace();
            }
            
            System.out.println("Simulation completed");
            
        } catch (Exception e) {
            System.err.println("Error in simple game test: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private static Deck loadDeck(String deckPath) {
        File deckFile = new File(deckPath);
        if (!deckFile.exists()) {
            System.out.println("Deck file not found: " + deckPath);
            return null;
        }
        
        try {
            return DeckSerializer.fromFile(deckFile);
        } catch (Exception e) {
            System.out.println("Error loading deck: " + e.getMessage());
            return null;
        }
    }
}