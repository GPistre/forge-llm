#!/usr/bin/env python3
import os
import json
import logging
import time

from flask import Flask, request, jsonify
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Get OpenAI API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.warning("OPENAI_API_KEY not set. LLM requests will fail.")

# System prompt for the LLM
SYSTEM_PROMPT = """
You are a Commander AI for Magic: The Gathering, controlling a deck in a game.
You will receive a JSON representation of the current game state including:
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

Focus on playing strategically. Consider:
1. Mana efficiency
2. Card advantage
3. Board presence
4. Life totals
5. Commander synergies
6. Timing (when to play spells/abilities)

Base your decisions on the current game state and optimize for winning the game.
"""

@app.route('/act', methods=['POST'])
def act():
    t0 = time.time()
    try:
        # Get the game state JSON from the request
        game_state = request.json
        if not game_state:
            return jsonify({"error": "No game state provided"}), 400
        
        context = game_state.get("context", "unknown")
        logger.info(f"Received request with context: {context}")
        
        # Log request for debugging (truncated for brevity)
        logger.debug(f"Request: {json.dumps(game_state)[:500]}...")
        
        # Create messages for the OpenAI API
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(game_state, indent=2)}
        ]
        
        # Call the OpenAI API
        try:
            response = openai.chat.completions.create(
                model="gpt-4.1-nano",  # Or use a different model as needed
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {response_text}")
            
            # Parse the JSON response
            try:
                response_json = json.loads(response_text)
                logger.info(f"Sending response for context {context}, ({time.time() - t0:.2f}s to reply)")

                return jsonify(response_json)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from LLM response: {e}")
                # Try to extract JSON from response text if it contains non-JSON text
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json.loads(json_match.group(0))
                        logger.info(f"Successfully extracted JSON from response ({time.time() - t0:.2f}s to reply)")
                        return jsonify(extracted_json)
                    except:
                        pass
                
                # If we can't parse the JSON, return a default response based on context
                logger.warning("Returning default response")
                default_response = create_default_response(context, game_state)
                return jsonify(default_response)
        
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            default_response = create_default_response(context, game_state)
            return jsonify(default_response), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

def create_default_response(context, game_state):
    """Create a default response based on the context when LLM fails"""
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
    
    return {"action": "PASS"}

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 7860))
    
    # Run the Flask app
    logger.info(f"Starting LLM server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)