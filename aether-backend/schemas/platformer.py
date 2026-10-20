"""Versioned design contracts. Genre dispatch is explicit; v1 remains supported."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Section(Contract):
    kind: Literal["meadow", "ruins", "factory", "ascent", "gauntlet"]
    length: int = Field(default=6, ge=4, le=10)
    elevation: int = Field(default=0, ge=-1, le=2)
    gap: int = Field(default=2, ge=1, le=3)
    enemies: bool = True
    hazards: bool = False


class GameDesign(Contract):
    title: str = Field(min_length=1, max_length=80)
    premise: str = Field(min_length=1, max_length=500)
    genre: Literal["platformer"] = "platformer"
    theme: Literal["forest", "industrial", "twilight"] = "forest"
    difficulty: Literal["relaxed", "balanced", "challenging"] = "balanced"
    objective: Literal["reach_exit", "collect_and_exit"] = "collect_and_exit"
    abilities: list[Literal["double_jump", "dash"]] = Field(default_factory=list, max_length=2)
    checkpoints: bool = True
    moving_platforms: bool = False
    sections: list[Section] = Field(min_length=5, max_length=14)
    unsupported: list[str] = Field(default_factory=list, max_length=20)
    design_notes: list[str] = Field(default_factory=list, max_length=20)


class Platform(Contract):
    x: int
    y: int
    width: int = Field(ge=4, le=10)
    kind: str
    moving: bool = False


class Entity(Contract):
    x: float
    y: float
    kind: Literal["crystal", "enemy", "spikes", "checkpoint", "exit"]
    platform: int


class Player(Contract):
    speed: float = 250
    jump: float = 490
    gravity: float = 1100
    health: int = 3
    abilities: list[str]


class PlatformerIR(Contract):
    schema_version: Literal["2.0"] = "2.0"
    genre: Literal["platformer"] = "platformer"
    title: str
    theme: str
    seed: int
    tile_size: int = 36
    width: int
    height: int
    spawn: dict[str, float]
    player: Player
    objective: dict
    platforms: list[Platform]
    entities: list[Entity]
    asset_pack: Literal["kenney_pixel_platformer"] = "kenney_pixel_platformer"
