#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json
import time
import sys
import os
import logging
import re
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
import datetime
import os

# Create logs directory if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Generate log filename with timestamp
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{log_dir}/llm_server_{timestamp}.log"
conversation_log = f"{log_dir}/conversation_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a separate logger for conversation details
conversation_logger = logging.getLogger("conversation")
conversation_logger.setLevel(logging.INFO)
conversation_handler = logging.FileHandler(conversation_log)
conversation_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
conversation_logger.addHandler(conversation_handler)
conversation_logger.propagate = False  # Don't propagate to root logger

# Initialize Flask app
app = Flask(__name__)

# Get OpenAI API key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.warning("OPENAI_API_KEY not set, using mock API key for testing")
    openai_api_key = "mock-api-key-for-testing"  # This won't work for real API calls
else:
    logger.info("OpenAI API key loaded successfully")
    
# Set up OpenAI client
openai_client = openai.OpenAI(api_key=openai_api_key)

# Store conversation history
conversation_history = {}

# System prompt for the LLM
SYSTEM_PROMPT = """
You are a Commander AI for Magic: The Gathering, controlling a deck in a game.
You will receive the current game state in a readable text format, including:
- Your player info (life, mana pool)
- Game phase information
- Cards on your battlefield
- Cards in your hand
- Your commander(s)
- Information about opponents and their boards
- The specific decision context (e.g., choosing an ability, declaring attackers)

Your task is to make the best strategic decision based on the current game state.

You MUST respond with a valid JSON object containing your decision.
Depending on the context, your response should include different fields:

For "chooseAbility" context:
{
  "action": "ACTIVATE",
  "spellAbilityId": "ability-id-from-input"
}

For "chooseTargets" context:
{
  "targets": ["card-id-1", "card-id-2", ...]
}

For "declareAttackers" context:
{
  "attackers": [
    {"cardId": "attacker-card-id", "defenderId": "defender-player-or-planeswalker-id"}
  ]
}

For "declareBlockers" context:
{
  "blockers": [
    {"blockerId": "blocker-card-id", "attackerId": "attacker-card-id"}
  ]
}

For "confirmAction" context:
{
  "confirm": true/false
}

For "chooseSingleEntity" context:
{
  "chosenId": "entity-id"
}

For "mulliganKeepHand" context:
{
  "keepHand": true/false
}

For "chooseSpellAbilityToPlay" context:
{
  "chosenAbilityId": integer-id-from-input
}
Use -1 for chosenAbilityId to indicate no action (passing priority).

Focus on playing strategically. Consider:
1. Mana efficiency
2. Card advantage
3. Board presence
4. Life totals
5. Commander synergies
6. Timing (when to play spells/abilities)

Base your decisions on the current game state and optimize for winning the game.
Do NOT provide any explanation, just the JSON response.
"""

@app.route("/", methods=["GET"])
def hello():
    return "LLM Service is running - OpenAI integration active"

def create_default_response(context, game_state):
    """Create a default response based on the context when LLM fails"""
    logger.info(f"Creating default response for context: {context}")
    
    if context == "chooseAbility":
        # Choose the first ability if available
        abilities = game_state.get("abilities", [])
        if abilities:
            return {"action": "ACTIVATE", "spellAbilityId": abilities[0].get("id")}
        return {"action": "PASS"}
    
    elif context == "chooseTargets":
        return {"targets": []}
    
    elif context == "declareAttackers":
        return {"attackers": []}
    
    elif context == "declareBlockers":
        return {"blockers": []}
    
    elif context == "confirmAction":
        return {"confirm": False}
    
    elif context == "chooseSingleEntity":
        options = game_state.get("chooseSingleEntity", {}).get("options", [])
        if options:
            return {"chosenId": options[0].get("id")}
        return {"chosenId": ""}
        
    elif context == "mulliganKeepHand":
        # Default to keeping the hand
        return {"keepHand": True}
    
    elif context == "chooseSpellAbilityToPlay":
        # Choose the first ability if available, or pass
        abilities = game_state.get("availableAbilities", [])
        if abilities:
            return {"chosenAbilityId": abilities[0].get("id")}
        return {"chosenAbilityId": -1}  # Pass if no abilities are available
    
    # Default response for unknown contexts
    return {"action": "PASS"}

@app.route("/act", methods=["POST"])
def act():
    t0 = time.time()

    try:
        # Get game state from request
        game_state = request.json
        if not game_state:
            logger.error("No game state provided in request")
            return jsonify({"error": "No game state provided"}), 400
        
        # Extract context from game state
        context = game_state.get("context", "unknown")
        logger.info(f"Request received with context: {context}")
        
        # Log request details (truncated for brevity)
        logger.debug(f"Request details: {json.dumps(game_state)[:500]}...")
        
        # Special handling for debug and testing contexts
        if context == "debug":
            logger.info("Debug context detected, returning PASS action")
            return jsonify({"action": "PASS"})
        elif context == "testing":
            logger.info("Testing context detected, returning test response")
            return jsonify({"action": "TEST_RESPONSE", "message": "Test successful"})
        
        # Check if context is valid
        valid_contexts = ["chooseAbility", "chooseTargets", "declareAttackers", 
                         "declareBlockers", "confirmAction", "chooseSingleEntity", "mulliganKeepHand", 
                         "chooseSpellAbilityToPlay"]
        
        if context not in valid_contexts:
            logger.warning(f"Invalid context: {context}")
            return jsonify({
                "error": f"Invalid game context '{context}'. Please provide a valid game context such as: {', '.join(valid_contexts)}"
            }), 400
        
        # Check if OpenAI API key is a real one (not our mock key)
        if openai_api_key == "mock-api-key-for-testing":
            logger.info(f"Using default response for context: {context} (mock API key)")
            default_response = create_default_response(context, game_state)
            return jsonify(default_response)
        
        # Format game state as plain text
        formatted_state = format_game_state_as_text(game_state)
        
        # Get or create conversation history for this player
        player_id = game_state.get("player", {}).get("name", 'unknown')
        if player_id not in conversation_history:
            conversation_history[player_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        
        # Add new message to conversation
        conversation_history[player_id].append({"role": "user", "content": formatted_state})
        
        # Use only the last few messages to avoid context length issues
        recent_messages = conversation_history[player_id][-10:] if len(conversation_history[player_id]) > 10 else conversation_history[player_id]
        
        # Log the formatted prompt sent to LLM
        conversation_logger.info(f"PLAYER: {player_id} | CONTEXT: {context}")
        conversation_logger.info("PROMPT:\n" + formatted_state)
        conversation_logger.info("-" * 50)
        # Call the OpenAI API
        try:
            logger.info(f"Calling OpenAI API for context: {context}")
            response = openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=recent_messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {response_text}")
            
            # Add assistant's response to conversation history
            conversation_history[player_id].append({"role": "assistant", "content": response_text})
            
            # Log the response from the LLM
            conversation_logger.info(f"PLAYER: {player_id} | RESPONSE:")
            conversation_logger.info(response_text)
            conversation_logger.info("=" * 80)
            
            # Parse the JSON response
            try:
                response_json = json.loads(response_text)
                logger.info(f"Successfully parsed LLM response: {response_json}")
                logger.info(f"({time.time() - t0:.2f}s to reply)")
                return jsonify(response_json)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from LLM response: {e}")
                # Try to extract JSON from response text if it contains non-JSON text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json.loads(json_match.group(0))
                        logger.info(f"Successfully extracted JSON from response  ({time.time() - t0:.2f}s to reply)")
                        logger.info(f"Successfully parsed LLM response: {extracted_json}")

                        return jsonify(extracted_json)
                    except json.JSONDecodeError:
                        logger.error("Failed to extract valid JSON from response")
                
                # If we can't parse the JSON, return a default response based on context
                logger.warning("Returning default response due to JSON parsing failure")
                default_response = create_default_response(context, game_state)
                return jsonify(default_response)
        
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            default_response = create_default_response(context, game_state)
            return jsonify(default_response)
    
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.exception(error_msg)
        return jsonify({"error": error_msg}), 500

def format_game_state_as_text(game_state):
    """Format the game state as plain text instead of JSON to minimize tokens"""
    context = game_state.get("context", "unknown")
    output = [f"Decision Context: {context}\n"]
    
    # Player info
    player_id = game_state.get("playerId", "unknown")
    player_info = game_state.get("player", {})
    life = player_info.get("life", 0)
    output.append(f"Your life: {life}")
    
    # Phase info
    phase = game_state.get("phase", "unknown")
    output.append(f"Current phase: {phase}\n")
    
    # Hand cards
    hand = game_state.get("hand", [])
    if hand:
        output.append("Cards in your hand:")
        for card in hand:
            name = card.get("name", "Unknown Card")
            card_id = card.get("id", "")
            mana_cost = card.get("manaCost", "")
            output.append(f"- {name} ({mana_cost}) [ID: {card_id}]")
        output.append("")
    
    # Battlefield
    battlefield = game_state.get("battlefield", [])
    if battlefield:
        output.append("Your battlefield:")
        for card in battlefield:
            name = card.get("name", "Unknown Card")
            card_id = card.get("id", "")
            tapped = "tapped" if card.get("tapped", False) else "untapped"
            output.append(f"- {name} ({tapped}) [ID: {card_id}]")
        output.append("")
    
    # Opponents
    opponents = game_state.get("opponents", [])
    if opponents:
        output.append("Opponents:")
        for opponent in opponents:
            opp_id = opponent.get("id", "unknown")
            opp_life = opponent.get("life", 0)
            output.append(f"Opponent [ID: {opp_id}] - Life: {opp_life}")
            
            # Opponent's battlefield
            opp_battlefield = opponent.get("battlefield", [])
            if opp_battlefield:
                output.append("  Battlefield:")
                for card in opp_battlefield:
                    name = card.get("name", "Unknown Card")
                    card_id = card.get("id", "")
                    tapped = "tapped" if card.get("tapped", False) else "untapped"
                    output.append(f"  - {name} ({tapped}) [ID: {card_id}]")
        output.append("")
    
    # Context-specific information
    if context == "chooseAbility":
        abilities = game_state.get("abilities", [])
        if abilities:
            output.append("Available abilities:")
            for ability in abilities:
                ability_id = ability.get("id", "")
                description = ability.get("description", "No description")
                output.append(f"- {description} [ID: {ability_id}]")
            output.append("")
    
    elif context == "chooseTargets":
        targets = game_state.get("targets", {})
        min_targets = targets.get("min", 0)
        max_targets = targets.get("max", 0)
        options = targets.get("options", [])
        output.append(f"Choose targets (min: {min_targets}, max: {max_targets}):")
        for option in options:
            option_id = option.get("id", "")
            name = option.get("name", "Unknown")
            output.append(f"- {name} [ID: {option_id}]")
        output.append("")
    
    elif context == "declareAttackers":
        attackers = game_state.get("attackers", {})
        potential = attackers.get("potential", [])
        defenders = attackers.get("defenders", [])
        
        output.append("Potential attackers:")
        for attacker in potential:
            attacker_id = attacker.get("id", "")
            name = attacker.get("name", "Unknown Card")
            output.append(f"- {name} [ID: {attacker_id}]")
        
        output.append("\nPotential defenders:")
        for defender in defenders:
            defender_id = defender.get("id", "")
            name = defender.get("name", "Unknown")
            life = defender.get("life", 0) if "life" in defender else "N/A"
            output.append(f"- {name} (Life: {life}) [ID: {defender_id}]")
        output.append("")
    
    elif context == "declareBlockers":
        blockers = game_state.get("blockers", {})
        potential = blockers.get("potential", [])
        attackers = blockers.get("attackers", [])
        
        output.append("Potential blockers:")
        for blocker in potential:
            blocker_id = blocker.get("id", "")
            name = blocker.get("name", "Unknown Card")
            output.append(f"- {name} [ID: {blocker_id}]")
        
        output.append("\nAttackers to block:")
        for attacker in attackers:
            attacker_id = attacker.get("id", "")
            name = attacker.get("name", "Unknown Card")
            output.append(f"- {name} [ID: {attacker_id}]")
        output.append("")
    
    elif context == "chooseSingleEntity":
        entity_choice = game_state.get("chooseSingleEntity", {})
        message = entity_choice.get("message", "Choose one:")
        options = entity_choice.get("options", [])
        
        output.append(f"{message}")
        for option in options:
            option_id = option.get("id", "")
            name = option.get("name", "Unknown")
            output.append(f"- {name} [ID: {option_id}]")
        output.append("")
    
    elif context == "mulliganKeepHand":
        hand = game_state.get("hand", [])
        output.append("Mulligan decision for hand:")
        for card in hand:
            name = card.get("name", "Unknown Card")
            mana_cost = card.get("manaCost", "")
            output.append(f"- {name} ({mana_cost})")
        output.append("")
    
    elif context == "chooseSpellAbilityToPlay":
        abilities = game_state.get("availableAbilities", [])
        if abilities:
            output.append("Available cards and abilities to play:")
            for ability in abilities:
                ability_id = ability.get("id", "")
                card_name = ability.get("hostCard", "Unknown Card")
                description = ability.get("description", "No description")
                is_land = ability.get("isLand", False)
                cost = ability.get("costDescription", "No cost")
                
                if is_land:
                    output.append(f"- Play land: {card_name} [ID: {ability_id}]")
                else:
                    output.append(f"- {card_name}: {description} (Cost: {cost}) [ID: {ability_id}]")
                
                # Add targeting info if available
                targets = ability.get("potentialTargets", [])
                if targets:
                    output.append("  Potential targets:")
                    for target in targets[:5]:  # Limit to first 5 targets to save space
                        target_name = target.get("name", "Unknown")
                        output.append(f"  * {target_name}")
                    if len(targets) > 5:
                        output.append(f"  * ... and {len(targets) - 5} more targets")
            
            output.append("\nChoose an ability ID to play or pass (-1).")
            output.append("")
    
    return "\n".join(output)

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 7861))
    
    # Log the start of the server
    logger.info(f"Starting LLM service on port {port}")
    logger.info(f"Main log file: {log_filename}")
    logger.info(f"Conversation log file: {conversation_log}")
    print(f"Starting LLM service on port {port}", flush=True)
    print(f"Logs will be written to:\n- {log_filename}\n- {conversation_log}")
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=port, debug=False)

