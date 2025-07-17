# Forge Spectator Mode Implementation Guide

## Overview
This guide details how to build a web-based spectator interface for Forge games, allowing real-time viewing of AI vs AI, AI vs LLM, or LLM vs LLM matches with action history navigation.

## Architecture

### Components
1. **Java Side (Forge)**:
   - Game State Broadcaster
   - Event Interceptor
   - WebSocket/HTTP Client

2. **Python Server**:
   - WebSocket/HTTP Server
   - Game State Storage
   - Action History Management
   - Static File Server

3. **HTML/JS Frontend**:
   - Game Board Visualization
   - Action Console
   - Navigation Controls
   - Scryfall Card Image Integration

## Step-by-Step Implementation

### Step 1: Java - Create Game State Broadcaster

Create `forge-game/src/main/java/forge/game/spectator/GameStateBroadcaster.java`:

```java
package forge.game.spectator;

import com.google.common.eventbus.Subscribe;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import forge.game.*;
import forge.game.event.*;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.zone.ZoneType;
import java.io.IOException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

public class GameStateBroadcaster {
    private final String serverEndpoint;
    private final HttpClient httpClient;
    private final Gson gson;
    private final Game game;
    private int actionSequence = 0;
    
    public GameStateBroadcaster(Game game, String endpoint) {
        this.game = game;
        this.serverEndpoint = endpoint;
        this.gson = new Gson();
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
        
        // Subscribe to game events
        game.subscribeToEvents(this);
        
        // Send initial game state
        sendGameState("game_start", null);
    }
    
    private JsonObject createGameStateSnapshot() {
        JsonObject state = new JsonObject();
        state.addProperty("gameId", game.getId().toString());
        state.addProperty("actionSequence", actionSequence++);
        state.addProperty("timestamp", System.currentTimeMillis());
        
        // Players
        JsonArray players = new JsonArray();
        for (Player p : game.getPlayers()) {
            JsonObject playerObj = new JsonObject();
            playerObj.addProperty("name", p.getName());
            playerObj.addProperty("life", p.getLife());
            playerObj.addProperty("handSize", p.getCardsIn(ZoneType.Hand).size());
            playerObj.addProperty("librarySize", p.getCardsIn(ZoneType.Library).size());
            
            // Battlefield
            JsonArray battlefield = new JsonArray();
            for (Card c : p.getCardsIn(ZoneType.Battlefield)) {
                battlefield.add(createCardJson(c));
            }
            playerObj.add("battlefield", battlefield);
            
            // Graveyard
            JsonArray graveyard = new JsonArray();
            for (Card c : p.getCardsIn(ZoneType.Graveyard)) {
                graveyard.add(createCardJson(c));
            }
            playerObj.add("graveyard", graveyard);
            
            players.add(playerObj);
        }
        state.add("players", players);
        
        // Current phase
        PhaseHandler ph = game.getPhaseHandler();
        JsonObject phase = new JsonObject();
        phase.addProperty("turn", ph.getTurn());
        phase.addProperty("phase", ph.getPhase().toString());
        phase.addProperty("activePlayer", ph.getPlayerTurn().getName());
        state.add("phase", phase);
        
        // Stack
        JsonArray stack = new JsonArray();
        for (SpellAbilityStackInstance si : game.getStack()) {
            JsonObject stackItem = new JsonObject();
            stackItem.addProperty("name", si.getSourceCard().getName());
            stackItem.addProperty("controller", si.getActivatingPlayer().getName());
            stackItem.addProperty("description", si.getStackDescription());
            stack.add(stackItem);
        }
        state.add("stack", stack);
        
        return state;
    }
    
    private JsonObject createCardJson(Card card) {
        JsonObject cardObj = new JsonObject();
        cardObj.addProperty("id", card.getId());
        cardObj.addProperty("name", card.getName());
        cardObj.addProperty("type", card.getType().toString());
        cardObj.addProperty("power", card.getNetPower());
        cardObj.addProperty("toughness", card.getNetToughness());
        cardObj.addProperty("tapped", card.isTapped());
        cardObj.addProperty("controller", card.getController().getName());
        
        // For Scryfall image lookup
        cardObj.addProperty("set", card.getSetCode());
        cardObj.addProperty("collectorNumber", card.getCollectorNumber());
        
        return cardObj;
    }
    
    private void sendGameState(String eventType, String description) {
        JsonObject payload = new JsonObject();
        payload.addProperty("eventType", eventType);
        payload.addProperty("description", description);
        payload.add("gameState", createGameStateSnapshot());
        
        String json = gson.toJson(payload);
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(serverEndpoint + "/game-event"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .timeout(Duration.ofSeconds(5))
            .build();
            
        // Send asynchronously to avoid blocking game
        CompletableFuture<HttpResponse<String>> future = 
            httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString());
            
        future.exceptionally(ex -> {
            System.err.println("Failed to send game state: " + ex.getMessage());
            return null;
        });
    }
    
    // Event handlers
    @Subscribe
    public void onCardPlayed(GameEventSpellAbilityCast event) {
        String desc = event.sa.getActivatingPlayer().getName() + " plays " + 
                     event.sa.getHostCard().getName();
        sendGameState("spell_cast", desc);
    }
    
    @Subscribe
    public void onSpellResolved(GameEventSpellResolved event) {
        String desc = event.spell.getHostCard().getName() + " resolves";
        sendGameState("spell_resolved", desc);
    }
    
    @Subscribe
    public void onPhaseChange(GameEventTurnPhase event) {
        String desc = "Phase: " + event.phaseType + " (" + 
                     event.playerTurn.getName() + ")";
        sendGameState("phase_change", desc);
    }
    
    @Subscribe
    public void onCombatDeclared(GameEventAttackersDeclared event) {
        sendGameState("attackers_declared", "Combat declared");
    }
    
    @Subscribe
    public void onDamageDealt(GameEventCardDamaged event) {
        String desc = event.card.getName() + " takes " + 
                     event.amount + " damage";
        sendGameState("damage_dealt", desc);
    }
    
    @Subscribe
    public void onGameEnd(GameEventGameOutcome event) {
        sendGameState("game_end", "Game ended");
    }
}
```

### Step 2: Modify SimulateMatch to Use Broadcaster

Update `forge-gui-desktop/src/main/java/forge/view/SimulateMatch.java`:

```java
// Add to simulateSingleMatch method, after creating the game:
if (System.getProperty("spectator.enabled", "false").equals("true")) {
    String spectatorEndpoint = System.getProperty("spectator.endpoint", 
                                                 "http://localhost:8080");
    new GameStateBroadcaster(g1, spectatorEndpoint);
}
```

### Step 3: Python Server Implementation

Create `spectator-server/server.py`:

```python
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory game storage
games = {}
game_lock = threading.Lock()

class GameSession:
    def __init__(self, game_id):
        self.game_id = game_id
        self.actions = []
        self.current_state = None
        self.created_at = datetime.now()
        self.is_live = True
        
    def add_action(self, event_data):
        action = {
            'sequence': len(self.actions),
            'timestamp': datetime.now().isoformat(),
            'eventType': event_data['eventType'],
            'description': event_data['description'],
            'gameState': event_data['gameState']
        }
        self.actions.append(action)
        self.current_state = event_data['gameState']
        
        # Broadcast to connected clients
        socketio.emit('game_action', {
            'gameId': self.game_id,
            'action': action
        }, room=self.game_id)
        
        # Mark as complete if game ended
        if event_data['eventType'] == 'game_end':
            self.is_live = False

@app.route('/game-event', methods=['POST'])
def game_event():
    """Receive game events from Forge"""
    try:
        data = request.json
        game_state = data['gameState']
        game_id = game_state['gameId']
        
        with game_lock:
            if game_id not in games:
                games[game_id] = GameSession(game_id)
            
            games[game_id].add_action(data)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error processing game event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/games', methods=['GET'])
def list_games():
    """List all games"""
    with game_lock:
        game_list = []
        for game_id, session in games.items():
            game_list.append({
                'gameId': game_id,
                'createdAt': session.created_at.isoformat(),
                'actionCount': len(session.actions),
                'isLive': session.is_live,
                'players': [p['name'] for p in session.current_state['players']] 
                          if session.current_state else []
            })
    return jsonify(game_list)

@app.route('/game/<game_id>', methods=['GET'])
def get_game(game_id):
    """Get full game data"""
    with game_lock:
        if game_id not in games:
            return jsonify({'error': 'Game not found'}), 404
        
        session = games[game_id]
        return jsonify({
            'gameId': game_id,
            'createdAt': session.created_at.isoformat(),
            'isLive': session.is_live,
            'actions': session.actions,
            'currentState': session.current_state
        })

@app.route('/')
def index():
    """Serve the main spectator UI"""
    return render_template('index.html')

@socketio.on('join_game')
def handle_join_game(data):
    """Join a game room for live updates"""
    game_id = data['gameId']
    join_room(game_id)
    emit('joined_game', {'gameId': game_id})

@socketio.on('leave_game')
def handle_leave_game(data):
    """Leave a game room"""
    game_id = data['gameId']
    leave_room(game_id)
    emit('left_game', {'gameId': game_id})

# Cleanup old games periodically
def cleanup_old_games():
    while True:
        time.sleep(3600)  # Every hour
        cutoff_time = datetime.now() - timedelta(hours=24)
        with game_lock:
            to_remove = []
            for game_id, session in games.items():
                if not session.is_live and session.created_at < cutoff_time:
                    to_remove.append(game_id)
            for game_id in to_remove:
                del games[game_id]

cleanup_thread = threading.Thread(target=cleanup_old_games, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
```

### Step 4: HTML/JS Frontend

Create `spectator-server/templates/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Forge Spectator Mode</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #1a1a1a;
            color: #fff;
        }
        
        .container {
            display: grid;
            grid-template-columns: 250px 1fr 300px;
            height: 100vh;
        }
        
        .game-list {
            background: #2a2a2a;
            padding: 10px;
            overflow-y: auto;
        }
        
        .game-board {
            display: flex;
            flex-direction: column;
            padding: 20px;
        }
        
        .player-area {
            flex: 1;
            border: 2px solid #444;
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        
        .battlefield {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            min-height: 150px;
        }
        
        .card {
            width: 100px;
            height: 140px;
            border: 1px solid #666;
            border-radius: 5px;
            cursor: pointer;
            position: relative;
            background-size: cover;
            background-position: center;
        }
        
        .card.tapped {
            transform: rotate(90deg);
            margin: 20px;
        }
        
        .action-log {
            background: #2a2a2a;
            padding: 10px;
            overflow-y: auto;
            font-size: 12px;
        }
        
        .controls {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 5px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .controls button {
            padding: 5px 15px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .controls button:hover {
            background: #45a049;
        }
        
        .controls button:disabled {
            background: #666;
            cursor: not-allowed;
        }
        
        .phase-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 5px;
        }
        
        .stack {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9);
            border: 2px solid #FFD700;
            padding: 10px;
            border-radius: 5px;
            max-width: 300px;
            z-index: 100;
        }
        
        .action-entry {
            padding: 5px;
            border-bottom: 1px solid #333;
        }
        
        .action-entry:hover {
            background: #333;
            cursor: pointer;
        }
        
        .player-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-weight: bold;
        }
        
        .game-item {
            padding: 10px;
            margin: 5px 0;
            background: #333;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .game-item:hover {
            background: #444;
        }
        
        .game-item.live {
            border-left: 3px solid #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="game-list" id="gameList">
            <h3>Games</h3>
            <div id="gameListContent"></div>
        </div>
        
        <div class="game-board">
            <div class="phase-indicator" id="phaseIndicator">
                Turn: <span id="turnNumber">0</span> | 
                Phase: <span id="phaseName">-</span>
            </div>
            
            <div class="player-area" id="opponent">
                <div class="player-info">
                    <span id="opponentName">Opponent</span>
                    <span>Life: <span id="opponentLife">20</span></span>
                </div>
                <div class="battlefield" id="opponentBattlefield"></div>
            </div>
            
            <div class="stack" id="stack" style="display: none;">
                <h4>Stack</h4>
                <div id="stackContent"></div>
            </div>
            
            <div class="player-area" id="player">
                <div class="player-info">
                    <span id="playerName">Player</span>
                    <span>Life: <span id="playerLife">20</span></span>
                </div>
                <div class="battlefield" id="playerBattlefield"></div>
            </div>
        </div>
        
        <div class="action-log" id="actionLog">
            <h3>Action Log</h3>
            <div id="actionLogContent"></div>
        </div>
    </div>
    
    <div class="controls">
        <button id="prevAction" onclick="navigateAction(-1)">Previous</button>
        <span id="actionIndex">0 / 0</span>
        <button id="nextAction" onclick="navigateAction(1)">Next</button>
        <button id="playPause" onclick="togglePlayback()">Pause</button>
        <input type="range" id="speedControl" min="0.1" max="2" step="0.1" value="1">
        <span id="speedLabel">1x</span>
    </div>

    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        let currentGame = null;
        let currentActionIndex = 0;
        let isPlaying = true;
        let playbackSpeed = 1;
        let playbackTimer = null;
        
        // Card image cache
        const cardImageCache = {};
        
        // Initialize
        loadGameList();
        
        function loadGameList() {
            fetch('/games')
                .then(res => res.json())
                .then(games => {
                    const content = document.getElementById('gameListContent');
                    content.innerHTML = '';
                    
                    games.forEach(game => {
                        const div = document.createElement('div');
                        div.className = `game-item ${game.isLive ? 'live' : ''}`;
                        div.innerHTML = `
                            <div>${game.players.join(' vs ')}</div>
                            <div style="font-size: 10px;">
                                ${game.isLive ? 'LIVE' : 'Completed'} | 
                                ${game.actionCount} actions
                            </div>
                        `;
                        div.onclick = () => loadGame(game.gameId);
                        content.appendChild(div);
                    });
                });
        }
        
        function loadGame(gameId) {
            // Leave previous game room
            if (currentGame) {
                socket.emit('leave_game', {gameId: currentGame.gameId});
            }
            
            fetch(`/game/${gameId}`)
                .then(res => res.json())
                .then(game => {
                    currentGame = game;
                    currentActionIndex = game.actions.length - 1;
                    
                    // Join game room for live updates
                    socket.emit('join_game', {gameId: game.gameId});
                    
                    // Display initial state
                    displayGameState(game.actions[currentActionIndex]);
                    updateActionLog();
                    updateControls();
                    
                    // Start playback if live
                    if (game.isLive && isPlaying) {
                        startPlayback();
                    }
                });
        }
        
        function displayGameState(action) {
            if (!action || !action.gameState) return;
            
            const state = action.gameState;
            
            // Update phase indicator
            document.getElementById('turnNumber').textContent = 
                state.phase.turn;
            document.getElementById('phaseName').textContent = 
                state.phase.phase;
            
            // Update players (assuming 2 players)
            if (state.players.length >= 2) {
                updatePlayer(state.players[0], 'player');
                updatePlayer(state.players[1], 'opponent');
            }
            
            // Update stack
            updateStack(state.stack);
        }
        
        function updatePlayer(player, elementId) {
            document.getElementById(`${elementId}Name`).textContent = 
                player.name;
            document.getElementById(`${elementId}Life`).textContent = 
                player.life;
            
            const battlefield = document.getElementById(`${elementId}Battlefield`);
            battlefield.innerHTML = '';
            
            player.battlefield.forEach(card => {
                const cardDiv = createCardElement(card);
                battlefield.appendChild(cardDiv);
            });
        }
        
        function createCardElement(card) {
            const div = document.createElement('div');
            div.className = `card ${card.tapped ? 'tapped' : ''}`;
            div.title = `${card.name}\n${card.type}\n${card.power}/${card.toughness}`;
            
            // Load Scryfall image
            loadCardImage(card, div);
            
            return div;
        }
        
        async function loadCardImage(card, element) {
            const cacheKey = `${card.set}_${card.collectorNumber}`;
            
            if (cardImageCache[cacheKey]) {
                element.style.backgroundImage = `url(${cardImageCache[cacheKey]})`;
                return;
            }
            
            try {
                // Use Scryfall API to get card image
                const response = await fetch(
                    `https://api.scryfall.com/cards/${card.set}/${card.collectorNumber}`
                );
                const data = await response.json();
                
                if (data.image_uris && data.image_uris.normal) {
                    cardImageCache[cacheKey] = data.image_uris.normal;
                    element.style.backgroundImage = `url(${data.image_uris.normal})`;
                }
            } catch (error) {
                console.error('Failed to load card image:', error);
                // Fallback to text display
                element.innerHTML = `<div style="padding: 5px;">${card.name}</div>`;
            }
        }
        
        function updateStack(stack) {
            const stackDiv = document.getElementById('stack');
            const stackContent = document.getElementById('stackContent');
            
            if (stack && stack.length > 0) {
                stackDiv.style.display = 'block';
                stackContent.innerHTML = stack.map(item => 
                    `<div>${item.description}</div>`
                ).join('');
            } else {
                stackDiv.style.display = 'none';
            }
        }
        
        function updateActionLog() {
            if (!currentGame) return;
            
            const content = document.getElementById('actionLogContent');
            content.innerHTML = '';
            
            currentGame.actions.forEach((action, index) => {
                const div = document.createElement('div');
                div.className = 'action-entry';
                if (index === currentActionIndex) {
                    div.style.background = '#444';
                }
                div.innerHTML = `
                    <strong>${action.eventType}</strong>: ${action.description}
                `;
                div.onclick = () => jumpToAction(index);
                content.appendChild(div);
            });
            
            // Scroll to current action
            const entries = content.getElementsByClassName('action-entry');
            if (entries[currentActionIndex]) {
                entries[currentActionIndex].scrollIntoView({block: 'center'});
            }
        }
        
        function navigateAction(delta) {
            if (!currentGame) return;
            
            currentActionIndex = Math.max(0, 
                Math.min(currentGame.actions.length - 1, 
                         currentActionIndex + delta));
            
            displayGameState(currentGame.actions[currentActionIndex]);
            updateActionLog();
            updateControls();
        }
        
        function jumpToAction(index) {
            currentActionIndex = index;
            displayGameState(currentGame.actions[currentActionIndex]);
            updateActionLog();
            updateControls();
        }
        
        function updateControls() {
            if (!currentGame) return;
            
            document.getElementById('actionIndex').textContent = 
                `${currentActionIndex + 1} / ${currentGame.actions.length}`;
            
            document.getElementById('prevAction').disabled = 
                currentActionIndex === 0;
            document.getElementById('nextAction').disabled = 
                currentActionIndex === currentGame.actions.length - 1;
        }
        
        function togglePlayback() {
            isPlaying = !isPlaying;
            document.getElementById('playPause').textContent = 
                isPlaying ? 'Pause' : 'Play';
            
            if (isPlaying && currentGame && currentGame.isLive) {
                startPlayback();
            } else {
                stopPlayback();
            }
        }
        
        function startPlayback() {
            stopPlayback();
            
            playbackTimer = setInterval(() => {
                if (currentActionIndex < currentGame.actions.length - 1) {
                    navigateAction(1);
                }
            }, 1000 / playbackSpeed);
        }
        
        function stopPlayback() {
            if (playbackTimer) {
                clearInterval(playbackTimer);
                playbackTimer = null;
            }
        }
        
        // Speed control
        document.getElementById('speedControl').addEventListener('input', (e) => {
            playbackSpeed = parseFloat(e.target.value);
            document.getElementById('speedLabel').textContent = `${playbackSpeed}x`;
            
            if (isPlaying && currentGame && currentGame.isLive) {
                startPlayback();
            }
        });
        
        // Socket.io event handlers
        socket.on('game_action', (data) => {
            if (currentGame && data.gameId === currentGame.gameId) {
                currentGame.actions.push(data.action);
                
                // Auto-advance if playing and at the end
                if (isPlaying && 
                    currentActionIndex === currentGame.actions.length - 2) {
                    currentActionIndex = currentGame.actions.length - 1;
                    displayGameState(data.action);
                    updateActionLog();
                    updateControls();
                }
            }
            
            // Update game list
            loadGameList();
        });
        
        // Refresh game list periodically
        setInterval(loadGameList, 10000);
    </script>
</body>
</html>
```

### Step 5: Build and Run Instructions

1. **Java Side - Add dependencies to `forge-game/pom.xml`**:
```xml
<dependency>
    <groupId>java.net.http</groupId>
    <artifactId>httpclient</artifactId>
    <version>11</version>
</dependency>
```

2. **Build Forge**:
```bash
mvn clean package -pl forge-game,forge-ai,forge-gui-desktop
```

3. **Set up Python server**:
```bash
cd spectator-server
pip install flask flask-cors flask-socketio
python server.py
```

4. **Run simulation with spectator mode**:
```bash
java -Dllm.endpoint="http://localhost:7861" \
     -Dspectator.enabled="true" \
     -Dspectator.endpoint="http://localhost:8080" \
     -jar forge-gui-desktop/target/forge-gui-desktop-*-jar-with-dependencies.jar \
     sim -f Commander -d "deck1.dck" "deck2.dck" -c "llm,ai" -n 1
```

5. **Access the UI**: Open http://localhost:8080 in your browser

## Important Gotchas and Considerations

### 1. Thread Safety
- Game events fire on the game thread
- HTTP calls must be async to avoid blocking gameplay
- Use CompletableFuture for non-blocking network calls

### 2. Memory Management
- Large games generate many events
- Implement cleanup for completed games
- Consider pagination for action history

### 3. Performance Impact
- Broadcasting adds overhead to each game action
- Use a queue system for high-frequency events
- Batch updates where possible

### 4. Scryfall API Limits
- Cache card images aggressively
- Implement rate limiting (10 requests/second)
- Consider pre-downloading card images

### 5. Game State Serialization
- Some Forge objects don't serialize cleanly
- Avoid circular references in JSON
- Extract only necessary data

### 6. Network Failures
- Spectator mode should never crash the game
- Implement circuit breakers for network calls
- Log but don't throw on broadcast failures

### 7. Security Considerations
- Don't expose sensitive game data
- Validate all inputs on the Python server
- Use authentication for production deployments

### 8. Forge Initialization
- FModel must be initialized before using game objects
- SimulateMatch already handles this correctly
- Be careful with static initialization order

## Extensions and Improvements

1. **Replay System**: Save games to database for later replay
2. **Multiple Views**: Add different board layouts (commander, modern, etc.)
3. **Statistics**: Track win rates, popular cards, etc.
4. **Commentary**: Add AI-generated commentary using LLM
5. **Mobile Support**: Responsive design for mobile viewing
6. **Deck Lists**: Show full deck lists and sideboard
7. **Search**: Search through action history
8. **Filters**: Filter actions by type (combat, spells, etc.)

This implementation provides a solid foundation for a spectator mode that can handle any game format and controller combination in Forge.