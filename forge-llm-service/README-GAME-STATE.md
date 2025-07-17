# Magic: The Gathering Game State Reference

This document provides a reference for the game state JSON structure passed by Forge to the LLM service.

## Game State JSON Structure

The game state JSON includes the following main components:

### General Information

- `context`: The current decision context (e.g., "chooseAbility", "declareAttackers")
- `gamePhase`: Information about the current game phase
  - `currentPhase`: The current phase (e.g., "MAIN1", "COMBAT_DECLARE_ATTACKERS")
  - `currentTurn`: The current turn number
  - `isPlayerTurn`: Whether it's the player's turn

### Player Information

- `player`: Information about the player
  - `name`: The player's name
  - `life`: The player's life total
  - `manaPool`: The player's available mana by color

### Board State

- `battlefield`: Array of cards on the player's battlefield
- `hand`: Array of cards in the player's hand
- `commanders`: Array of the player's commander(s)
- `opponents`: Array of opponent information
  - Each opponent has `name`, `life`, `battlefield`, and `commanders` fields

### Context-Specific Information

Depending on the `context` value, additional fields may be present:

- `chooseAbility`: Abilities the player can activate
  - `abilities`: Array of available abilities
- `chooseTargets`: Targets the player can choose
  - `targets`: Array of valid targets
- `declareAttackers`: Information for declaring attackers
  - `attackers`: Array of valid attackers
- `declareBlockers`: Information for declaring blockers
  - `attackers`: Array of attacking creatures
  - `blockers`: Array of valid blockers
- `confirmAction`: Information about an action to confirm
  - `actionDescription`: Description of the action
- `chooseSingleEntity`: Options for choosing a single entity
  - `choices`: Array of entities that can be chosen

## Card Information

Each card in the game state contains:

- `id`: Unique identifier for the card
- `name`: The card's name
- `type`: The card's type line
- `power`: Power (for creatures)
- `toughness`: Toughness (for creatures)
- `text`: The card's rules text
- `isTapped`: Whether the card is tapped
- `canAttack`: Whether the card can attack
- `canBlock`: Whether the card can block
- Additional properties depending on the card type

## Ability Information

Each ability in the game state contains:

- `id`: Unique identifier for the ability
- `hostCard`: Name of the card the ability belongs to
- `description`: Short description of the ability
- `toString`: String representation of the ability

## Response Format

The LLM service must return a JSON object with a structure that matches the current context:

### chooseAbility

```json
{
  "action": "ACTIVATE",
  "spellAbilityId": "ability-id-from-input"
}
```

Or to pass:

```json
{
  "action": "PASS"
}
```

### chooseTargets

```json
{
  "targets": ["card-id-1", "card-id-2", ...]
}
```

### declareAttackers

```json
{
  "attackers": [
    {"cardId": "attacker-card-id", "defenderId": "defender-player-or-planeswalker-id"}
  ]
}
```

### declareBlockers

```json
{
  "blockers": [
    {"blockerId": "blocker-card-id", "attackerId": "attacker-card-id"}
  ]
}
```

### confirmAction

```json
{
  "confirm": true
}
```

### chooseSingleEntity

```json
{
  "chosenId": "entity-id"
}
```