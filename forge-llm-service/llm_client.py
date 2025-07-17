"""
Magic: The Gathering LLM Client for OpenAI integration

This module handles communication with OpenAI's API to generate Magic: The Gathering
game decisions based on the current game state. It provides utility functions for
creating prompts, processing responses, and handling different game contexts.
"""

import os
import json
import logging
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("llm_client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_client")

# Initialize OpenAI client with API key from environment variable
try:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not found in environment variables. Using fallback behavior.")
    else:
        openai.api_key = OPENAI_API_KEY
        logger.info("OpenAI API key loaded successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")

# Model to use for API calls
DEFAULT_MODEL = "gpt-4-turbo"

# System prompt that explains the task to the LLM
SYSTEM_PROMPT = """
You are an expert Magic: The Gathering player helping to play a game through the Forge MTG application.
Your task is to analyze the current game state and make the optimal decision for the player.

You will receive information about:
- Current game context (what decision needs to be made)
- Player's hand, battlefield, commanders, life total, and mana pool
- Opponent's battlefield, commanders, and life total
- Available abilities, attack options, block options, or targets

Respond with ONLY a JSON object containing your decision. Include no explanation or commentary.
Your response must match the expected format for the current context.
"""

# Context-specific prompt templates
PROMPT_TEMPLATES = {
    "chooseAbility": """
Analyze the current game state where you need to choose an ability to activate.

Available abilities:
{abilities}

Current phase: {phase}
Your turn: {is_player_turn}
Your life: {player_life}
Opponent life: {opponent_life}

Your battlefield:
{player_battlefield}

Opponent's battlefield:
{opponent_battlefield}

Your hand:
{player_hand}

Based on this information, which ability should you activate?
Respond with only a JSON object: {"action": "CHOOSE_ABILITY", "abilityId": "<id of chosen ability>"}
If you want to pass without activating an ability, respond with: {"action": "PASS"}
""",

    "chooseTargets": """
Analyze the current game state where you need to choose targets for a spell or ability.

Available targets:
{targets}

Current phase: {phase}
Your turn: {is_player_turn}
Your life: {player_life}
Opponent life: {opponent_life}

Your battlefield:
{player_battlefield}

Opponent's battlefield:
{opponent_battlefield}

Your hand:
{player_hand}

Based on this information, which target(s) should you choose?
Respond with only a JSON object: {"action": "CHOOSE_TARGETS", "targetIds": ["<id1>", "<id2>", ...]}
""",

    "declareAttackers": """
Analyze the current game state where you need to declare attackers.

Potential attackers:
{attackers}

Current phase: {phase}
Your turn: {is_player_turn}
Your life: {player_life}
Opponent life: {opponent_life}

Your battlefield:
{player_battlefield}

Opponent's battlefield:
{opponent_battlefield}

Your hand:
{player_hand}

Based on this information, which creatures should attack?
Respond with only a JSON object: {"action": "DECLARE_ATTACKERS", "attackers": ["<id1>", "<id2>", ...]}
If you want to attack with no creatures, respond with: {"action": "DECLARE_ATTACKERS", "attackers": []}
""",

    "declareBlockers": """
Analyze the current game state where you need to declare blockers.

Attacking creatures:
{attackers}

Potential blockers:
{blockers}

Current phase: {phase}
Your turn: {is_player_turn}
Your life: {player_life}
Opponent life: {opponent_life}

Your battlefield:
{player_battlefield}

Opponent's battlefield:
{opponent_battlefield}

Your hand:
{player_hand}

Based on this information, how should you block?
Respond with only a JSON object: {"action": "DECLARE_BLOCKERS", "blocks": [{"blocker": "<blockerId>", "attacker": "<attackerId>"}, ...]}
If you want to block with no creatures, respond with: {"action": "DECLARE_BLOCKERS", "blocks": []}
""",

    "confirmAction": """
Analyze the current game state where you need to confirm or cancel an action.

Action to confirm:
{action_description}

Current phase: {phase}
Your turn: {is_player_turn}
Your life: {player_life}
Opponent life: {opponent_life}

Your battlefield:
{player_battlefield}

Opponent's battlefield:
{opponent_battlefield}

Your hand:
{player_hand}

Based on this information, should you confirm or cancel this action?
Respond with only a JSON object: {"action": "CONFIRM"} or {"action": "CANCEL"}
""",

    "chooseSingleEntity": """
Analyze the current game state where you need to choose a single entity.

Available choices:
{choices}

Current phase: {phase}
Your turn: {is_player_turn}
Your life: {player_life}
Opponent life: {opponent_life}

Your battlefield:
{player_battlefield}

Opponent's battlefield:
{opponent_battlefield}

Your hand:
{player_hand}

Based on this information, which entity should you choose?
Respond with only a JSON object: {"action": "CHOOSE_ENTITY", "entityId": "<id of chosen entity>"}
"""
}

def format_card_list(cards):
    """Format a list of cards into a readable string."""
    if not cards:
        return "None"
    
    result = []
    for card in cards:
        card_desc = f"- {card.get('name', 'Unknown')} ({card.get('type', 'Unknown')})"
        if "Creature" in card.get('type', ''):
            card_desc += f" {card.get('power', 0)}/{card.get('toughness', 0)}"
        card_desc += f" - {card.get('text', 'No text')}"
        result.append(card_desc)
    
    return "\n".join(result)

def format_abilities(abilities):
    """Format a list of abilities into a readable string."""
    if not abilities:
        return "No abilities available"
    
    result = []
    for ability in abilities:
        ability_desc = f"- ID: {ability.get('id', 'Unknown')}, {ability.get('hostCard', 'Unknown')}: {ability.get('toString', ability.get('description', 'Unknown'))}"
        result.append(ability_desc)
    
    return "\n".join(result)

def create_prompt(game_state):
    """Create a context-specific prompt based on the game state."""
    context = game_state.get("context", "unknown")
    
    if context not in PROMPT_TEMPLATES:
        logger.warning(f"Unknown context: {context}, using default response")
        return f"Game state has unknown context: {context}. Please provide a valid context."
    
    # Extract common game state information
    player = game_state.get("player", {})
    player_life = player.get("life", 0)
    
    game_phase = game_state.get("gamePhase", {})
    phase = game_phase.get("currentPhase", "UNKNOWN")
    is_player_turn = "Yes" if game_phase.get("isPlayerTurn", False) else "No"
    
    player_battlefield = format_card_list(game_state.get("battlefield", []))
    player_hand = format_card_list(game_state.get("hand", []))
    
    opponents = game_state.get("opponents", [])
    opponent_life = opponents[0].get("life", 0) if opponents else 0
    opponent_battlefield = format_card_list(opponents[0].get("battlefield", [])) if opponents else "None"
    
    # Context-specific information
    context_specific = {}
    if context == "chooseAbility":
        context_specific["abilities"] = format_abilities(game_state.get("abilities", []))
    elif context == "chooseTargets":
        context_specific["targets"] = format_card_list(game_state.get("targets", []))
    elif context == "declareAttackers":
        context_specific["attackers"] = format_card_list([c for c in game_state.get("battlefield", []) if c.get("canAttack", False)])
    elif context == "declareBlockers":
        context_specific["attackers"] = format_card_list(game_state.get("attackers", []))
        context_specific["blockers"] = format_card_list([c for c in game_state.get("battlefield", []) if c.get("canBlock", False)])
    elif context == "confirmAction":
        context_specific["action_description"] = game_state.get("actionDescription", "Unknown action")
    elif context == "chooseSingleEntity":
        context_specific["choices"] = format_card_list(game_state.get("choices", []))
    
    # Combine with template
    template = PROMPT_TEMPLATES[context]
    prompt = template.format(
        phase=phase,
        is_player_turn=is_player_turn,
        player_life=player_life,
        opponent_life=opponent_life,
        player_battlefield=player_battlefield,
        opponent_battlefield=opponent_battlefield,
        player_hand=player_hand,
        **context_specific
    )
    
    return prompt

def get_default_response(context):
    """Get a default response for a given context in case of error."""
    if context == "chooseAbility":
        return {"action": "PASS"}
    elif context == "chooseTargets":
        return {"action": "CHOOSE_TARGETS", "targetIds": []}
    elif context == "declareAttackers":
        return {"action": "DECLARE_ATTACKERS", "attackers": []}
    elif context == "declareBlockers":
        return {"action": "DECLARE_BLOCKERS", "blocks": []}
    elif context == "confirmAction":
        return {"action": "CONFIRM"}
    elif context == "chooseSingleEntity":
        return {"action": "CHOOSE_ENTITY", "entityId": None}
    else:
        return {"action": "PASS", "message": "Default fallback response"}

def get_llm_decision(game_state):
    """
    Get a decision from the LLM based on the game state.
    
    Args:
        game_state (dict): The current game state
        
    Returns:
        dict: The LLM's decision
    """
    # Handle special cases
    if not game_state:
        return {"action": "PASS", "message": "Empty game state received"}
    
    context = game_state.get("context")
    
    # If in debug or testing mode, return predefined responses
    if context == "debug":
        return {"action": "PASS", "message": "Debug mode - passing"}
    if context == "testing":
        return {"action": "TEST_RESPONSE", "message": "Test successful"}
        
    # If we don't have a valid API key, return a default response
    if not OPENAI_API_KEY:
        logger.warning("No OpenAI API key available, using default response")
        return get_default_response(context)
    
    try:
        # Create prompt for the current game state
        user_prompt = create_prompt(game_state)
        
        # Make API call to OpenAI
        logger.info(f"Sending request to OpenAI for context: {context}")
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic responses
            max_tokens=500
        )
        
        # Extract and parse the response
        llm_response_text = response.choices[0].message.content.strip()
        
        # Try to parse the JSON response
        try:
            llm_response = json.loads(llm_response_text)
            logger.info(f"LLM response: {llm_response}")
            return llm_response
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {llm_response_text}")
            logger.info("Using default response instead")
            return get_default_response(context)
            
    except Exception as e:
        logger.error(f"Error getting LLM decision: {e}")
        return get_default_response(context)

if __name__ == "__main__":
    # Test the client with a sample game state
    with open("sample-state.json", "r") as f:
        sample_state = json.load(f)
    
    decision = get_llm_decision(sample_state)
    print(f"Decision: {decision}")