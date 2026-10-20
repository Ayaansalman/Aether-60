"""
Mock Model Provider for offline testing and deterministic GameIR generation.
Conforms to Section 7.2 of the AETHER specification.
"""

import json
import re
import time
from typing import Any, Dict, List

from providers.base import REPAIR_AGENT_MARKER, CompletionResult, ModelProvider

MOCK_LABEL = "MOCK PROVIDER: not a real model, results are not evidence"

# Deliberately unplayable (valid) GameIR. Must stay identical to
# aether-frontend/src/game/sample-too-hard.json (enforced by tests/test_repair.py).
TOO_HARD_SPEC: Dict[str, Any] = {
    "schema_version": "1.0",
    "title": "Neon Gauntlet (Too Hard)",
    "genre": "arena_survival",
    "premise": "Twelve overclocked drones sprint at you and one hit ends the run. A deliberately unplayable spec used to exercise the repair loop.",
    "theme": "sci_fi",
    "player": {"move_speed": 220, "max_health": 1, "attack_mode": "avoid_only"},
    "enemies": [{"type": "chaser", "count": 12, "speed": 240}],
    "collectibles": [],
    "objective": {"type": "survive_seconds", "target": 30},
    "difficulty": 5,
    "controls": {"movement": "WASD or arrow keys"},
    "seed": 42,
}


class MockModelProvider:
    """
    Offline model provider that generates valid GameIR JSON specs based on
    sample game designs in aether-frontend/src/game, matching keywords like
    'spooky', 'pirate', 'robot'/'sci-fi', 'cozy', and 'hard'.
    """

    def __init__(self, model_name: str = "mock-planner-v1"):
        self.model_name = model_name

    def complete(self, system: str, user: str) -> CompletionResult:
        if REPAIR_AGENT_MARKER in system:
            return self._complete_repair(user)

        start_time = time.time()
        user_lower = user.lower()

        # Offline repair-loop demo: a prompt containing "repair demo" yields the known too-hard spec
        # (valid GameIR that fails the spec-level playability checks).
        if "repair demo" in user_lower:
            demo_response = {
                "spec": TOO_HARD_SPEC,
                "limitations": [f"[{MOCK_LABEL}] Returned the fixed too-hard demo spec for the repair loop."],
            }
            return CompletionResult(
                text=json.dumps(demo_response, indent=2),
                model=self.model_name,
                latency_ms=max(1, int((time.time() - start_time) * 1000)),
                usage={"prompt_tokens": len(system) // 4, "completion_tokens": len(json.dumps(demo_response)) // 4, "total_tokens": 100},
            )

        difficulty = 3

        # Keyword-based variety routing
        if "spooky wizard" in user_lower:
            # Preserves exact test expectations for "spooky wizard"
            theme = "spooky"
            title = "Wizard Crystal Rush"
            premise = "Collect crystals while ghosts chase the player in the arena."
            arena_layout = "open"
            player_speed = 220.0
            max_health = 3
            attack_mode = "projectile"
            enemies = [{"type": "chaser", "count": 5, "speed": 75.0}]
            collectibles = [{"type": "crystal", "count": 10}]
            objective = {"type": "collect_count", "target": 8}
            controls = {"movement": "WASD or arrow keys", "attack": "Space"}
            overrides = {
                "player_label": "WIZARD",
                "enemy_label": "GHOST",
                "collectible_label": "CRYSTAL",
                "player_shape": "triangle",
                "enemy_shape": "circle",
                "accent_hex": "#a855f7",
            }
        elif any(k in user_lower for k in ["flappy", "lanes", "frogger", "crossy"]):
            theme = "cozy"
            title = "Crossy Patrol Lanes"
            premise = "Cross guarded horizontal lanes to collect harvest berries."
            arena_layout = "lanes"
            player_speed = 200.0
            max_health = 3
            attack_mode = "avoid_only"
            enemies = [{"type": "patroller", "count": 4, "speed": 70.0}]
            collectibles = [{"type": "star", "count": 10}]
            objective = {"type": "collect_count", "target": 8}
            controls = {"movement": "WASD or arrow keys", "attack": None}
            overrides = {
                "player_label": "FROGGER",
                "enemy_label": "PATROL",
                "collectible_label": "BERRY",
                "player_shape": "circle",
                "enemy_shape": "square",
                "accent_hex": "#10b981",
            }
        elif any(k in user_lower for k in ["invaders", "shooter"]):
            theme = "spooky"
            title = "Invader Bullet Bastion"
            premise = "Evade sniper volleys behind solid pillars while returning fire."
            arena_layout = "pillars"
            player_speed = 220.0
            max_health = 3
            attack_mode = "projectile"
            enemies = [{"type": "shooter", "count": 3, "speed": 60.0}]
            collectibles = []
            objective = {"type": "survive_seconds", "target": 30}
            controls = {"movement": "WASD or arrow keys", "attack": "Space"}
            overrides = {
                "player_label": "DEFENDER",
                "enemy_label": "INVADER",
                "player_shape": "triangle",
                "enemy_shape": "circle",
                "accent_hex": "#f59e0b",
            }
        elif any(k in user_lower for k in ["maze", "pacman"]):
            theme = "pirate"
            title = "Maze Crystal Runner"
            premise = "Navigate wide corridors to collect pirate doubloons."
            arena_layout = "maze"
            player_speed = 200.0
            max_health = 3
            attack_mode = "avoid_only"
            enemies = [{"type": "chaser", "count": 3, "speed": 65.0}]
            collectibles = [{"type": "coin", "count": 10}]
            objective = {"type": "collect_count", "target": 6}
            controls = {"movement": "WASD or arrow keys", "attack": None}
            overrides = {
                "player_label": "PACRUNNER",
                "enemy_label": "GHOST",
                "collectible_label": "DOUBLOON",
                "player_shape": "diamond",
                "enemy_shape": "square",
                "accent_hex": "#eab308",
            }
        elif any(k in user_lower for k in ["bounce", "pinball"]):
            theme = "sci_fi"
            title = "Pinball Pillar Arena"
            premise = "Dodge high-speed ricocheting bouncers amidst solid pillars."
            arena_layout = "pillars"
            player_speed = 210.0
            max_health = 3
            attack_mode = "avoid_only"
            enemies = [{"type": "bouncer", "count": 4, "speed": 75.0}]
            collectibles = [{"type": "gem", "count": 10}]
            objective = {"type": "collect_count", "target": 8}
            controls = {"movement": "WASD or arrow keys", "attack": None}
            overrides = {
                "player_label": "BALL",
                "enemy_label": "BOUNCER",
                "collectible_label": "BUMPER",
                "player_shape": "circle",
                "enemy_shape": "diamond",
                "accent_hex": "#06b6d4",
            }
        elif any(k in user_lower for k in ["boss", "dash"]):
            theme = "fantasy"
            title = "Dasher Duel Arena"
            premise = "Stalk and strike lunging dashers with precision melee blows."
            arena_layout = "open"
            player_speed = 220.0
            max_health = 4
            attack_mode = "melee"
            enemies = [{"type": "dasher", "count": 4, "speed": 70.0}]
            collectibles = []
            objective = {"type": "defeat_enemies", "target": 5}
            controls = {"movement": "WASD or arrow keys", "attack": "Space to melee swing"}
            overrides = {
                "player_label": "HERO",
                "enemy_label": "DASHER",
                "player_shape": "diamond",
                "enemy_shape": "triangle",
                "accent_hex": "#8b5cf6",
            }
        else:
            # General keyword-based theme resolution
            arena_layout = "open"
            overrides = None
            player_speed = 220.0
            if "spooky" in user_lower:
                theme = "spooky"
                title = "Wizard Crystal Rush"
                premise = "Collect crystals while ghostly chasers pursue the wizard in a haunted arena."
                col_type = "crystal"
            elif "pirate" in user_lower:
                theme = "pirate"
                title = "Pirate Captain's Cove"
                premise = "Survive the stormy cove while rival pirate chasers attempt to capture the ship."
                col_type = "coin"
            elif any(k in user_lower for k in ["robot", "sci-fi", "scifi", "cyber"]):
                theme = "sci_fi"
                title = "Neon Cybernetic Survival"
                premise = "Outmaneuver rogue robotic drones in the neon cyber arena."
                col_type = "battery"
            elif "cozy" in user_lower:
                theme = "cozy"
                title = "Cozy Garden Gathering"
                premise = "Collect fallen gems while gentle forest critters chase you around the garden."
                col_type = "gem"
            else:
                theme = "fantasy"
                if any(w in user_lower for w in ["hard", "difficult", "extreme"]):
                    title = "Enchanted Arena Survival (Hard Mode)"
                    premise = "Survive the relentless pursuit of high-speed chaser golems in the punishing arena."
                else:
                    title = "Enchanted Arena Survival"
                    premise = "Collect magical stars while fantasy chaser golems pursue the hero."
                col_type = "star"

            # Determine objective and attack mode
            is_survive = any(w in user_lower for w in ["survive", "survival", "survives", "seconds", "timer"])
            is_defeat = any(w in user_lower for w in ["defeat", "kill", "eliminate", "slay", "destroy"])
            is_melee = any(w in user_lower for w in ["melee", "slash", "sword", "punch"])

            if is_defeat:
                attack_mode = "melee" if is_melee else "projectile"
                objective = {"type": "defeat_enemies", "target": 5}
                collectibles = []
                controls = {
                    "movement": "WASD or arrow keys",
                    "attack": "Space",
                }
            elif is_survive:
                attack_mode = "melee" if is_melee else "avoid_only"
                target_seconds = 30
                sec_match = re.search(r"(\d+)\s*(?:seconds?|secs?|s\b)", user_lower)
                if sec_match:
                    try:
                        val = int(sec_match.group(1))
                        target_seconds = max(5, min(120, val))
                    except ValueError:
                        pass
                objective = {
                    "type": "survive_seconds",
                    "target": target_seconds,
                }
                collectibles = []
                controls = {
                    "movement": "WASD or arrow keys",
                }
            else:
                attack_mode = "melee" if is_melee else "projectile"
                objective = {
                    "type": "collect_count",
                    "target": 8,
                }
                collectibles = [
                    {
                        "type": col_type,
                        "count": 10,
                    }
                ]
                controls = {
                    "movement": "WASD or arrow keys",
                    "attack": "Space" if attack_mode != "avoid_only" else None,
                }

            is_hard = any(w in user_lower for w in ["hard", "difficult", "extreme", "expert", "nightmare"])
            difficulty = 5 if is_hard else 2
            enemy_count = 10 if is_hard else 5
            enemy_speed = 110.0 if is_hard else 75.0
            max_health = 2 if is_hard else 3
            enemies = [{"type": "chaser", "count": enemy_count, "speed": enemy_speed}]

        # Build limitations for unsupported requests
        limitations: List[str] = [f"[{MOCK_LABEL}] Synthesized by offline mock provider."]
        if "3d" in user_lower:
            limitations.append("3D graphics requested; adapted to top-down 2D arena survival.")
        if any(w in user_lower for w in ["multiplayer", "coop", "co-op", "pvp"]):
            limitations.append("Multiplayer requested; adapted to single-player arena survival.")
        if any(w in user_lower for w in ["fps", "open world", "platformer", "racing", "gravity", "flappy", "jump"]):
            limitations.append("Non-arena genre / gravity platformer requested; adapted to top-down 2D arena survival.")

        spec: Dict[str, Any] = {
            "schema_version": "1.0",
            "title": title,
            "genre": "arena_survival",
            "premise": premise,
            "theme": theme,
            "arena_layout": arena_layout,
            "player": {
                "move_speed": player_speed,
                "max_health": max_health,
                "attack_mode": attack_mode,
            },
            "enemies": enemies,
            "collectibles": collectibles,
            "objective": objective,
            "difficulty": difficulty,
            "controls": controls,
            "seed": 42,
        }
        if overrides:
            spec["visual_overrides"] = overrides

        response_obj = {
            "spec": spec,
            "limitations": limitations,
        }

        latency_ms = max(1, int((time.time() - start_time) * 1000))
        return CompletionResult(
            text=json.dumps(response_obj, indent=2),
            model=self.model_name,
            latency_ms=latency_ms,
            usage={"prompt_tokens": len(system) // 4, "completion_tokens": len(json.dumps(response_obj)) // 4, "total_tokens": 100},
        )

    def _complete_repair(self, user: str) -> CompletionResult:
        """
        MOCK REPAIR RESPONDER (deterministic rules, not a model; only active for MODEL_PROVIDER=mock).
        Makes the spec easier for the failed playability checks:
        enemy speed <= 45% of player speed, <= 6 enemies, >= 3 HP, difficulty <= 3.
        If the spec already satisfies those rules it tightens progressively (x0.75 speed, -1 enemy, +1 HP),
        so repeated repairs never return a no-op.
        """
        start_time = time.time()
        spec_match = re.search(r"<<<SPEC>>>\s*([\s\S]*?)\s*<<<END_SPEC>>>", user)
        spec: Dict[str, Any] = json.loads(spec_match.group(1)) if spec_match else {}
        player = spec.get("player", {})
        enemy = (spec.get("enemies") or [{}])[0]

        move = float(player.get("move_speed", 220.0))
        hp = int(player.get("max_health", 3))
        speed = float(enemy.get("speed", 75.0))
        count = int(enemy.get("count", 5))
        difficulty = int(spec.get("difficulty", 2))

        new_speed = min(speed, 0.45 * move)
        new_count = min(count, 6)
        new_hp = max(hp, 3)
        new_difficulty = min(difficulty, 3)

        if (new_speed, new_count, new_hp, new_difficulty) == (speed, count, hp, difficulty):
            new_speed = speed * 0.75
            new_count = max(1, count - 1)
            new_hp = min(10, hp + 1)

        patch: Dict[str, Any] = {}
        if abs(new_speed - speed) > 1e-9:
            patch["enemy_speed_multiplier"] = round(new_speed / speed, 4)
        if new_count != count:
            patch["enemy_count"] = new_count
        if new_hp != hp:
            patch["player_max_health"] = new_hp
        if new_difficulty != difficulty:
            patch["difficulty"] = new_difficulty
        patch["rationale"] = (
            f"[{MOCK_LABEL}] Deterministic rule-based repair: enemies ({count} at {speed:g}px/s) overwhelmed a "
            f"player with {hp} HP moving at {move:g}px/s. Lowering enemy speed to <=45% of player speed, capping "
            f"enemies at 6 and guaranteeing >=3 HP makes the round survivable."
        )

        return CompletionResult(
            text=json.dumps(patch, indent=2),
            model=self.model_name,
            latency_ms=max(1, int((time.time() - start_time) * 1000)),
            usage={"prompt_tokens": len(user) // 4, "completion_tokens": len(json.dumps(patch)) // 4, "total_tokens": 100},
        )
