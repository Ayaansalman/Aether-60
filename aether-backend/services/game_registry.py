"""
Game Registry Service for AETHER.
Maintains canonical definitions and sample specifications for built-in demo routes,
including variety mechanics: enemy behaviours (bouncer, patroller, dasher, shooter),
arena layouts (pillars, lanes, maze), defeat_enemies objective, and visual overrides.
"""

from typing import Any, Dict, List, Optional
from schemas.game_ir import GameIR

# Canonical variety demo specifications
DEMO_BOUNCER_PILLARS_SPEC: Dict[str, Any] = {
    "schema_version": "1.0",
    "title": "Pinball Bouncer Arena",
    "genre": "arena_survival",
    "premise": "Dodge fast bouncers ricocheting off symmetric pillar obstacles in a high-tech cyber arena.",
    "theme": "sci_fi",
    "arena_layout": "pillars",
    "visual_overrides": {
        "player_label": "CYBER RUNNER",
        "enemy_label": "PINBALL BOT",
        "player_shape": "diamond",
        "enemy_shape": "diamond",
        "accent_hex": "#06b6d4",
    },
    "player": {
        "move_speed": 220.0,
        "max_health": 4,
        "attack_mode": "projectile",
    },
    "enemies": [
        {
            "type": "bouncer",
            "count": 6,
            "speed": 100.0,
        }
    ],
    "collectibles": [],
    "objective": {
        "type": "survive_seconds",
        "target": 20,
    },
    "difficulty": 3,
    "controls": {
        "movement": "WASD or arrow keys",
        "attack": "Space",
    },
    "seed": 101,
}

DEMO_PATROL_LANES_SPEC: Dict[str, Any] = {
    "schema_version": "1.0",
    "title": "Crossy Patrol Lanes",
    "genre": "arena_survival",
    "premise": "Navigate horizontal lane barriers with safe gaps while avoiding rhythmic patroller guards.",
    "theme": "pirate",
    "arena_layout": "lanes",
    "visual_overrides": {
        "player_label": "CAPTAIN",
        "enemy_label": "PATROLLER",
        "collectible_label": "DOUBLOONS",
        "player_shape": "square",
        "enemy_shape": "square",
        "accent_hex": "#f59e0b",
    },
    "player": {
        "move_speed": 220.0,
        "max_health": 3,
        "attack_mode": "avoid_only",
    },
    "enemies": [
        {
            "type": "patroller",
            "count": 6,
            "speed": 90.0,
        }
    ],
    "collectibles": [
        {
            "type": "coin",
            "count": 8,
        }
    ],
    "objective": {
        "type": "collect_count",
        "target": 5,
    },
    "difficulty": 3,
    "controls": {
        "movement": "WASD or arrow keys",
        "attack": None,
    },
    "seed": 202,
}

DEMO_DASHER_DEFEAT_SPEC: Dict[str, Any] = {
    "schema_version": "1.0",
    "title": "Shadow Dasher Showdown",
    "genre": "arena_survival",
    "premise": "Bait lunging dashers into missed strikes, then counter-attack with melee slashes to clear the arena.",
    "theme": "spooky",
    "arena_layout": "open",
    "visual_overrides": {
        "player_label": "GHOST HUNTER",
        "enemy_label": "SHADOW DASHER",
        "player_shape": "triangle",
        "enemy_shape": "triangle",
        "accent_hex": "#a855f7",
    },
    "player": {
        "move_speed": 220.0,
        "max_health": 5,
        "attack_mode": "melee",
    },
    "enemies": [
        {
            "type": "dasher",
            "count": 4,
            "speed": 110.0,
        }
    ],
    "collectibles": [],
    "objective": {
        "type": "defeat_enemies",
        "target": 6,
    },
    "difficulty": 3,
    "controls": {
        "movement": "WASD or arrow keys",
        "attack": "Space",
    },
    "seed": 303,
}

DEMO_SHOOTER_PILLARS_SPEC: Dict[str, Any] = {
    "schema_version": "1.0",
    "title": "Pillar Shooter Gauntlet",
    "genre": "arena_survival",
    "premise": "Use symmetric pillar cover to weave between enemy projectiles and defeat turret sentinels.",
    "theme": "fantasy",
    "arena_layout": "pillars",
    "visual_overrides": {
        "player_label": "MAGE",
        "enemy_label": "SHOOTER TURRET",
        "player_shape": "circle",
        "enemy_shape": "circle",
        "accent_hex": "#10b981",
    },
    "player": {
        "move_speed": 220.0,
        "max_health": 4,
        "attack_mode": "projectile",
    },
    "enemies": [
        {
            "type": "shooter",
            "count": 4,
            "speed": 70.0,
        }
    ],
    "collectibles": [],
    "objective": {
        "type": "defeat_enemies",
        "target": 6,
    },
    "difficulty": 3,
    "controls": {
        "movement": "WASD or arrow keys",
        "attack": "Space",
    },
    "seed": 404,
}

DEMO_MAZE_COLLECT_SPEC: Dict[str, Any] = {
    "schema_version": "1.0",
    "title": "Enchanted Maze Wanderer",
    "genre": "arena_survival",
    "premise": "Gather fallen grove stars through wide inner corridors without getting cornered by woodland chasers.",
    "theme": "cozy",
    "arena_layout": "maze",
    "visual_overrides": {
        "player_label": "WANDERER",
        "enemy_label": "FOREST CRITTER",
        "collectible_label": "FALLEN STAR",
        "player_shape": "circle",
        "enemy_shape": "diamond",
        "accent_hex": "#a3e635",
    },
    "player": {
        "move_speed": 220.0,
        "max_health": 4,
        "attack_mode": "avoid_only",
    },
    "enemies": [
        {
            "type": "chaser",
            "count": 4,
            "speed": 70.0,
        }
    ],
    "collectibles": [
        {
            "type": "star",
            "count": 10,
        }
    ],
    "objective": {
        "type": "collect_count",
        "target": 6,
    },
    "difficulty": 2,
    "controls": {
        "movement": "WASD or arrow keys",
        "attack": None,
    },
    "seed": 505,
}

# Registry mapping route slug -> spec dictionary
REGISTRY: Dict[str, Dict[str, Any]] = {
    "demo-bouncer-pillars": DEMO_BOUNCER_PILLARS_SPEC,
    "demo-patrol-lanes": DEMO_PATROL_LANES_SPEC,
    "demo-dasher-defeat": DEMO_DASHER_DEFEAT_SPEC,
    "demo-shooter-pillars": DEMO_SHOOTER_PILLARS_SPEC,
    "demo-maze-collect": DEMO_MAZE_COLLECT_SPEC,
}


def get_demo_spec(key: str) -> Optional[Dict[str, Any]]:
    """Returns raw dictionary spec for a demo route key, if registered."""
    clean_key = key.replace("/play/", "").strip("/")
    return REGISTRY.get(clean_key)


get_registered_spec = get_demo_spec


def get_validated_demo_spec(key: str) -> Optional[GameIR]:
    """Returns a validated GameIR instance for a demo route key."""
    raw = get_demo_spec(key)
    if not raw:
        return None
    return GameIR.model_validate(raw)


def list_registered_demos() -> List[str]:
    """Returns list of registered demo route slugs."""
    return list(REGISTRY.keys())
