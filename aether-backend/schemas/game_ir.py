"""
GameIR (Game Intermediate Representation) v1.0 Pydantic Schema.
Conforms to Sections 5.1 and 5.2 of the 60% FYP Capstone Engineering Specification.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# Enums & Allowed Literals
GameGenre = Literal["arena_survival"]
GameTheme = Literal["fantasy", "sci_fi", "pirate", "spooky", "cozy"]
AttackMode = Literal["projectile", "melee", "avoid_only"]
EnemyType = Literal["chaser", "bouncer", "patroller", "dasher", "shooter"]
CollectibleType = Literal["crystal", "battery", "coin", "gem", "star"]
ObjectiveType = Literal["survive_seconds", "collect_count", "defeat_enemies"]
ArenaLayout = Literal["open", "pillars", "lanes", "maze"]
ShapeType = Literal["circle", "square", "triangle", "diamond"]


class VisualOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_label: Optional[str] = Field(None, max_length=24, description="Custom HUD label for player (max 24 chars)")
    enemy_label: Optional[str] = Field(None, max_length=24, description="Custom HUD label for enemy (max 24 chars)")
    collectible_label: Optional[str] = Field(None, max_length=24, description="Custom HUD label for collectible (max 24 chars)")
    player_shape: Optional[ShapeType] = Field(None, description="Geometric primitive shape for player")
    enemy_shape: Optional[ShapeType] = Field(None, description="Geometric primitive shape for enemies")
    accent_hex: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$", description="Custom accent hex color code (#RRGGBB)")


class PlayerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move_speed: float = Field(..., ge=100.0, le=300.0, description="Player speed clamped to [100, 300]")
    max_health: int = Field(..., ge=1, le=10, description="Player health clamped to [1, 10]")
    attack_mode: AttackMode


class EnemyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EnemyType
    count: int = Field(..., ge=1, le=50, description="Count of this enemy type")
    speed: float = Field(..., ge=20.0, le=250.0, description="Speed in pixels per second")


class CollectibleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: CollectibleType
    count: int = Field(..., ge=0, le=50, description="Quantity of collectible items")


class ObjectiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ObjectiveType
    target: int = Field(..., ge=1, description="Numeric target for the objective")

    @model_validator(mode="after")
    def validate_bounds(self) -> "ObjectiveConfig":
        if self.type == "survive_seconds":
            if not (5 <= self.target <= 120):
                raise ValueError(
                    f"Objective 'survive_seconds' target must be between 5 and 120 seconds, got {self.target}."
                )
        elif self.type == "collect_count":
            if not (1 <= self.target <= 20):
                raise ValueError(
                    f"Objective 'collect_count' target must be between 1 and 20 items, got {self.target}."
                )
        elif self.type == "defeat_enemies":
            if not (1 <= self.target <= 30):
                raise ValueError(
                    f"Objective 'defeat_enemies' target must be between 1 and 30 enemies, got {self.target}."
                )
        return self


class ControlsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    movement: str = Field(..., min_length=1, max_length=50)
    attack: Optional[str] = Field(None, max_length=50)


class GameIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(..., min_length=1, max_length=50, description="Game title (1-50 chars)")
    genre: GameGenre
    premise: str = Field(..., min_length=1, max_length=240, description="Short summary/premise (max 240 chars)")
    theme: GameTheme
    arena_layout: ArenaLayout = Field(default="open", description="Arena layout geometry")
    visual_overrides: Optional[VisualOverrides] = Field(default=None, description="Optional custom visual labels and shapes")
    player: PlayerConfig
    enemies: List[EnemyConfig] = Field(..., min_length=1, max_length=2, description="1 to 2 enemy types")
    collectibles: List[CollectibleConfig] = Field(default_factory=list, min_length=0, max_length=2, description="0 to 2 collectible types")
    objective: ObjectiveConfig
    difficulty: int = Field(..., ge=1, le=5, description="Difficulty rating 1 to 5")
    controls: ControlsConfig
    seed: Optional[int] = Field(None, description="Deterministic seed for repeatability")


class GameIRPatch(BaseModel):
    """
    Constrained patch schema for the self-repair loop (Section 5.3).
    Only allow-listed tunable fields are permitted. Arbitrary keys are rejected.
    """
    model_config = ConfigDict(extra="forbid")

    player_move_speed: Optional[float] = None
    player_max_health: Optional[int] = None
    enemy_speed_multiplier: Optional[float] = None
    enemy_count: Optional[int] = None
    objective_target: Optional[int] = None
    difficulty: Optional[int] = None
    rationale: Optional[str] = None


def apply_patch(spec: GameIR, patch: GameIRPatch) -> GameIR:
    """
    Applies an allow-listed GameIRPatch onto an existing GameIR specification.
    Clamps numeric values to their legal contract boundaries and revalidates.
    """
    data = spec.model_dump()

    # 1. Player move speed clamped to [100.0, 300.0]
    if patch.player_move_speed is not None:
        data["player"]["move_speed"] = max(100.0, min(300.0, float(patch.player_move_speed)))

    # 2. Player max health clamped to [1, 10]
    if patch.player_max_health is not None:
        data["player"]["max_health"] = max(1, min(10, patch.player_max_health))

    # 3. Enemy speed multiplier applied and clamped to [20.0, 250.0]
    if patch.enemy_speed_multiplier is not None and data.get("enemies"):
        for enemy in data["enemies"]:
            new_speed = enemy["speed"] * patch.enemy_speed_multiplier
            enemy["speed"] = max(20.0, min(250.0, float(new_speed)))

    # 4. Enemy count clamped to [1, 50]
    if patch.enemy_count is not None and data.get("enemies"):
        data["enemies"][0]["count"] = max(1, min(50, patch.enemy_count))

    # 5. Objective target clamped according to objective type
    if patch.objective_target is not None:
        if data["objective"]["type"] == "survive_seconds":
            data["objective"]["target"] = max(5, min(120, patch.objective_target))
        elif data["objective"]["type"] == "collect_count":
            data["objective"]["target"] = max(1, min(20, patch.objective_target))
        elif data["objective"]["type"] == "defeat_enemies":
            data["objective"]["target"] = max(1, min(30, patch.objective_target))

    # 6. Difficulty clamped to [1, 5]
    if patch.difficulty is not None:
        data["difficulty"] = max(1, min(5, patch.difficulty))

    # Revalidate full GameIR contract
    return GameIR.model_validate(data)
