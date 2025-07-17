package forge.view;

import forge.LobbyPlayer;
import forge.ai.LLMClient;
import forge.ai.LobbyPlayerLLM;
import forge.deck.Deck;
import forge.deck.io.DeckSerializer;
import forge.game.GameRules;
import forge.game.GameType;
import forge.game.Match;
import forge.game.player.RegisteredPlayer;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
import forge.player.GamePlayerUtil;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * Test class for simulating a match with an LLM controller.
 * Minimal implementation to avoid initialization issues.
 */
public class TestLLMSimulation {

    public static void main(String[] args) {
        try {
            System.out.println("Starting LLM Simulation Test");
            
            // Initialize Forge model with minimal setup
            try {
                FModel.initialize(null, null);
            } catch (Exception e) {
                System.out.println("Minimal initialization failed, attempting alternative initialization...");
                // Alternative initialization approach - just what we need for this test
                forge.util.FileUtil.ensureDirectoryExists(ForgeConstants.CACHE_DIR);
                forge.util.FileUtil.ensureDirectoryExists(ForgeConstants.USER_GAMES_DIR);
                forge.util.FileUtil.ensureDirectoryExists(ForgeConstants.DECK_CONSTRUCTED_DIR);
                forge.util.FileUtil.ensureDirectoryExists(ForgeConstants.DECK_COMMANDER_DIR);
            }
            System.out.println("Forge model initialized");
            
            // Set up LLM client
            String llmEndpoint = System.getProperty("llm.endpoint", "http://localhost:7860");
            System.out.println("Using LLM endpoint: " + llmEndpoint);
            LLMClient llmClient = new LLMClient(llmEndpoint);
            
            // Parse command line args (simplified)
            if (args.length < 1) {
                System.out.println("Usage: TestLLMSimulation <deckPath1> <deckPath2>");
                return;
            }
            
            // Load decks
            List<RegisteredPlayer> players = new ArrayList<>();
            GameType gameType = GameType.Commander;
            
            for (int i = 0; i < args.length; i++) {
                String deckPath = args[i];
                Deck deck = loadDeck(deckPath, gameType);
                if (deck == null) {
                    System.out.println("Failed to load deck: " + deckPath);
                    return;
                }
                
                System.out.println("Loaded deck: " + deck.getName());
                
                // Create player
                RegisteredPlayer rp = RegisteredPlayer.forCommander(deck);
                
                // First player uses LLM, second uses AI
                String playerName = (i == 0 ? "LLM-" : "AI-") + deck.getName();
                playerName = playerName.substring(0, Math.min(playerName.length(), 20)); // Truncate if too long
                
                if (i == 0) {
                    LobbyPlayer llmPlayer = new LobbyPlayerLLM(playerName, llmClient);
                    System.out.println("Created LLM player: " + llmPlayer.getName());
                    rp.setPlayer(llmPlayer);
                } else {
                    LobbyPlayer aiPlayer = GamePlayerUtil.createAiPlayer(playerName, i);
                    System.out.println("Created AI player: " + aiPlayer.getName());
                    rp.setPlayer(aiPlayer);
                }
                
                players.add(rp);
            }
            
            // Set up game rules
            GameRules rules = new GameRules(gameType);
            
            // Create and start match
            System.out.println("Creating match");
            Match match = new Match(rules, players, "Test Match");
            
            // Play a single game
            SimulateMatch.simulateSingleMatch(match, 0, true);
            
            System.out.println("Simulation completed");
            
        } catch (Exception e) {
            System.err.println("Error in LLM simulation: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private static Deck loadDeck(String deckPath, GameType gameType) {
        File deckFile = new File(deckPath);
        if (!deckFile.exists()) {
            // Try with commander path prefix
            String baseDir = gameType.equals(GameType.Commander) ? 
                ForgeConstants.DECK_COMMANDER_DIR : ForgeConstants.DECK_CONSTRUCTED_DIR;
            deckFile = new File(baseDir + deckPath);
            
            if (!deckFile.exists()) {
                System.out.println("Deck file not found: " + deckPath);
                return null;
            }
        }
        
        try {
            return DeckSerializer.fromFile(deckFile);
        } catch (Exception e) {
            System.out.println("Error loading deck: " + e.getMessage());
            return null;
        }
    }
}