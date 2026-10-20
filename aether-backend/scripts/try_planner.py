#!/usr/bin/env python3
"""
CLI utility to test and inspect the AETHER Game Planner.
Usage:
    python scripts/try_planner.py "your game prompt here"
"""

import json
import sys
from pathlib import Path

# Ensure backend root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "services").exists() else SCRIPT_DIR.parent / "aether-backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    backend_env = BACKEND_DIR / ".env"
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)
    else:
        load_dotenv()
except ImportError:
    pass

from providers.factory import get_provider
from providers.mock import MockModelProvider
from services.planner import plan_game


def evaluate_output(prompt: str, result) -> dict:
    """Evaluates whether the output matches the prompt and limitations are honest."""
    p_lower = prompt.lower()
    matches = True
    match_notes = []

    if not result.ok or not result.spec:
        return {
            "matches_prompt": False,
            "judgment": "FAILED - No valid specification generated.",
            "clear_limitations": False,
        }

    spec = result.spec

    # Theme check
    if "spooky" in p_lower and spec.theme != "spooky":
        matches = False
        match_notes.append(f"Expected spooky theme, got {spec.theme}")
    if "robot" in p_lower and spec.theme != "sci_fi":
        matches = False
        match_notes.append(f"Expected sci_fi theme, got {spec.theme}")

    # Objective check
    if "60 seconds" in p_lower:
        if spec.objective.type != "survive_seconds" or spec.objective.target != 60:
            matches = False
            match_notes.append(f"Expected survive_seconds target 60, got {spec.objective.type} {spec.objective.target}")

    # Difficulty check
    if "hard" in p_lower:
        if spec.difficulty < 4:
            matches = False
            match_notes.append(f"Expected high difficulty (>=4), got {spec.difficulty}")

    # Limitations check for 3D multiplayer
    has_3d_limitation = any("3d" in str(lim).lower() for lim in result.limitations)
    has_mp_limitation = any("multiplayer" in str(lim).lower() for lim in result.limitations)
    clear_limitations = True
    if ("3d" in p_lower or "multiplayer" in p_lower or "racing" in p_lower or "open world" in p_lower):
        clear_limitations = has_3d_limitation and has_mp_limitation
        if not clear_limitations:
            match_notes.append("Missing explicit 3D or multiplayer limitation")

    judgment_text = "PASS - Specification matches prompt intent"
    if clear_limitations and ("3d" in p_lower or "multiplayer" in p_lower):
        judgment_text += " with explicit, honest limitations (adapted to 2D single-player arena instead of pretending)"
    if not matches:
        judgment_text = "MISMATCH - " + "; ".join(match_notes)

    return {
        "matches_prompt": matches,
        "clear_limitations": clear_limitations,
        "judgment": judgment_text,
    }


def main():
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
    else:
        prompt = "a spooky wizard collecting crystals"

    provider = get_provider()
    is_mock = isinstance(provider, MockModelProvider)

    print("=" * 70)
    if is_mock:
        print("     MOCK PROVIDER: not a real model, results are not evidence")
        print("=" * 70)
    print("                 AETHER GAME PLANNER CLI")
    print("=" * 70)
    print(f"Prompt:    {prompt}")
    print(f"Provider:  {'mock' if is_mock else type(provider).__name__}")
    print("-" * 70)

    result = plan_game(prompt, provider=provider)

    print(f"Provider:                 {'mock' if is_mock else type(provider).__name__}")
    print(f"Status:                   {'OK' if result.ok else 'FAILED'}")
    if result.error_code:
        print(f"Error Code:               {result.error_code}")
    print(f"Attempts:                 {result.attempts}")
    print(f"Latency:                  {result.latency_ms} ms")
    print(f"First Response Validated: {'Yes' if result.first_response_validated else 'No'}")
    print(f"Model:                    {result.model}")
    print(f"Limitations List:         {result.limitations}")

    if result.ok and result.spec:
        spec = result.spec
        print("\nKey Fields of the Spec:")
        print("-" * 70)
        print(f"  Title:        {spec.title}")
        print(f"  Genre:        {spec.genre}")
        print(f"  Theme:        {spec.theme}")
        print(f"  Premise:      {spec.premise}")
        print(f"  Player:       speed={spec.player.move_speed}px/s, max_hp={spec.player.max_health}, attack={spec.player.attack_mode}")
        print(f"  Enemies:      {[{'type': e.type, 'count': e.count, 'speed': e.speed} for e in spec.enemies]}")
        print(f"  Collectibles: {[{'type': c.type, 'count': c.count} for c in spec.collectibles]}")
        print(f"  Objective:    type={spec.objective.type}, target={spec.objective.target}")
        print(f"  Difficulty:   {spec.difficulty} / 5")
        print(f"  Controls:     movement='{spec.controls.movement}', attack='{spec.controls.attack}'")

        eval_res = evaluate_output(prompt, result)
        print("\nEvaluation & Judgment:")
        print("-" * 70)
        print(f"  Matches Prompt:      {'YES' if eval_res['matches_prompt'] else 'NO'}")
        print(f"  Clear Limitations:   {'YES' if eval_res['clear_limitations'] else 'NO'}")
        print(f"  Verdict:             {eval_res['judgment']}")

        print("\nGenerated GameIR Specification (JSON):")
        print("-" * 70)
        print(json.dumps(spec.model_dump(), indent=2))
    else:
        print("\nErrors encountered:")
        print("-" * 70)
        for err in result.errors:
            print(f"- {err}")

    from providers.base import get_model_request_count
    print(f"Total Model Requests (process): {get_model_request_count()}")
    print("=" * 70)
    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
