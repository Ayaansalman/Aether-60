"""
Validator service for GameIR specifications.
Performs Pydantic schema validation followed by semantic and safety checks.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from schemas.game_ir import GameIR


@dataclass
class ValidationResult:
    ok: bool
    spec: Optional[GameIR] = None
    errors: List[str] = field(default_factory=list)


FORBIDDEN_REGEX_PATTERNS = [
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"=>"),
]


def validate_game_ir(raw: Dict[str, Any]) -> ValidationResult:
    """
    Validates a raw dictionary against the GameIR v1.0 schema and semantic rules.
    Returns a ValidationResult object with ok, spec, and human-readable error messages.
    """
    errors: List[str] = []

    # 1. Pydantic schema validation
    try:
        spec = GameIR.model_validate(raw)
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            errors.append(f"{loc}: {msg}" if loc else msg)
        return ValidationResult(ok=False, spec=None, errors=errors)
    except Exception as exc:
        return ValidationResult(ok=False, spec=None, errors=[str(exc)])

    # 2. Semantic Check: At least 1 enemy in total count
    total_enemies = sum(enemy.count for enemy in spec.enemies)
    if total_enemies < 1:
        errors.append("Semantic error: At least 1 total enemy must be configured.")

    # 3. Semantic Check: For collect_count, target must be <= total collectibles
    if spec.objective.type == "collect_count":
        total_collectibles = sum(c.count for c in spec.collectibles)
        if spec.objective.target > total_collectibles:
            errors.append(
                f"Semantic error: Objective target ({spec.objective.target}) exceeds total available collectibles ({total_collectibles})."
            )

    # 4. Semantic Check: defeat_enemies is invalid when attack_mode is avoid_only
    if spec.objective.type == "defeat_enemies" and spec.player.attack_mode == "avoid_only":
        errors.append(
            "Semantic error: Objective 'defeat_enemies' is invalid when player attack_mode is 'avoid_only'."
        )

    # 5. Semantic Safety Check: No code-like or URL-like regex matches in title, premise, or visual labels
    fields_to_check = [("title", spec.title), ("premise", spec.premise)]
    if spec.visual_overrides:
        if spec.visual_overrides.player_label:
            fields_to_check.append(("player_label", spec.visual_overrides.player_label))
        if spec.visual_overrides.enemy_label:
            fields_to_check.append(("enemy_label", spec.visual_overrides.enemy_label))
        if spec.visual_overrides.collectible_label:
            fields_to_check.append(("collectible_label", spec.visual_overrides.collectible_label))

    for field_name, value in fields_to_check:
        for pattern in FORBIDDEN_REGEX_PATTERNS:
            if pattern.search(value):
                errors.append(
                    f"Safety error: Code-like or URL pattern '{pattern.pattern}' detected in {field_name}."
                )

    if errors:
        return ValidationResult(ok=False, spec=None, errors=errors)

    return ValidationResult(ok=True, spec=spec, errors=[])
