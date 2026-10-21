"""Versioned design contracts. Genre dispatch is explicit; v1 remains supported."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Section(Contract):
    kind: Literal["meadow", "ruins", "factory", "ascent", "gauntlet", "cavern", "terraces", "bridge"]
    length: int = Field(default=6, ge=4, le=10)
    elevation: int = Field(default=0, ge=-1, le=2)
    gap: int = Field(default=2, ge=1, le=3)
    enemies: bool = True
    hazards: bool = False
    encounter: Literal["patrol", "chase", "shooter"] = "patrol"
    challenge: Literal['traversal', 'precision', 'combat', 'hazards', 'exploration', 'moving'] = 'traversal'


class RequestedFeature(Contract):
    source: str = Field(min_length=1, max_length=300)
    capability: Literal['ice_environment', 'forest_environment', 'factory_environment', 'slippery',
                        'falling_icicles', 'exit_indicator', 'collectibles', 'patrol', 'robots', 'chase',
                        'ranged', 'moving_platforms', 'timed_hazards', 'checkpoints', 'multiple_levels',
                        'double_jump', 'dash', 'unsupported']
    description: str = Field(min_length=1, max_length=300)


class LevelDesign(Contract):
    """A playable level; omitted settings inherit campaign defaults."""
    title: str = Field(min_length=1, max_length=80)
    theme: Literal['forest', 'industrial', 'twilight', 'ice'] | None = None
    topology: Literal['journey', 'ascent', 'terraces', 'cavern'] | None = None
    difficulty: Literal['relaxed', 'balanced', 'challenging'] | None = None
    objective: Literal['reach_exit', 'collect_and_exit'] | None = None
    slippery: bool | None = None
    falling_icicles: bool | None = None
    timed_hazards: bool | None = None
    moving_platforms: bool | None = None
    checkpoints: bool | None = None
    icicle_trigger: Literal['mixed', 'proximity', 'timer'] | None = None
    hazard_period_ms: int | None = Field(default=None, ge=800, le=10000)
    exit_style: Literal['shrine', 'gate', 'beacon'] | None = None
    exit_indicator: Literal['none', 'glow', 'pulse', 'flash'] | None = None
    collectible: Literal['crystals', 'relics'] | None = None
    briefing: str = Field(default='', max_length=200)
    sections: list[Section] = Field(min_length=5, max_length=14)


class GameDesign(Contract):
    title: str = Field(min_length=1, max_length=80)
    premise: str = Field(min_length=1, max_length=500)
    genre: Literal["platformer"] = "platformer"
    theme: Literal["forest", "industrial", "twilight", "ice"] = "forest"
    difficulty: Literal["relaxed", "balanced", "challenging"] = "balanced"
    objective: Literal["reach_exit", "collect_and_exit"] = "collect_and_exit"
    abilities: list[Literal["double_jump", "dash"]] = Field(default_factory=list, max_length=2)
    checkpoints: bool = True
    moving_platforms: bool = False
    slippery: bool = False
    falling_icicles: bool = False
    icicle_trigger: Literal['mixed', 'proximity', 'timer'] = 'mixed'
    hazard_period_ms: int = Field(default=2200, ge=800, le=10000)
    timed_hazards: bool = False
    exit_indicator: Literal["none", "glow", "pulse", "flash"] = "none"
    exit_style: Literal['shrine', 'gate', 'beacon'] = 'gate'
    collectible: Literal["crystals", "relics"] = "crystals"
    level_count: int = Field(default=1, ge=1, le=3)
    levels: list[LevelDesign] = Field(default_factory=list, max_length=3)
    topology: Literal["journey", "ascent", "terraces", "cavern"] = "journey"
    sections: list[Section] = Field(min_length=5, max_length=14)
    unsupported: list[str] = Field(default_factory=list, max_length=20)
    design_notes: list[str] = Field(default_factory=list, max_length=20)
    requested_features: list[RequestedFeature] = Field(default_factory=list, max_length=40)

    @model_validator(mode='after')
    def consistent_levels(self):
        if self.levels and len(self.levels) != self.level_count:
            raise ValueError('levels must contain exactly level_count level specifications')
        return self


class Platform(Contract):
    x: int
    y: int
    width: int = Field(ge=4, le=10)
    kind: str
    moving: bool = False
    route: Literal['main', 'optional'] = 'main'


class Entity(Contract):
    x: float
    y: float
    kind: Literal["crystal", "enemy", "spikes", "checkpoint", "exit", "icicle", "timed_hazard"]
    platform: int
    behavior: Literal["patrol", "chase", "shooter"] = "patrol"
    trigger: Literal["proximity", "timer"] = "proximity"
    period_ms: int = Field(default=2200, ge=800, le=10000)
    radius: int = Field(default=110, ge=40, le=400)


class Player(Contract):
    speed: float = 250
    jump: float = 490
    gravity: float = 1100
    health: int = 3
    abilities: list[str]


class LevelIR(Contract):
    title: str
    width: int
    height: int
    spawn: dict[str, float]
    objective: dict
    platforms: list[Platform]
    entities: list[Entity]
    camera_mode: Literal["follow", "vertical"] = "follow"
    theme: str | None = None
    slippery: bool | None = None
    exit_style: Literal['shrine', 'gate', 'beacon'] | None = None
    exit_indicator: Literal['none', 'glow', 'pulse', 'flash'] | None = None
    collectible: Literal['crystals', 'relics'] | None = None
    difficulty: Literal['relaxed', 'balanced', 'challenging'] = 'balanced'
    briefing: str = ''
    topology: Literal['journey', 'ascent', 'terraces', 'cavern'] = 'journey'


class PlatformerIR(LevelIR):
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
    slippery: bool = False
    exit_indicator: Literal["none", "glow", "pulse", "flash"] = "none"
    exit_style: Literal['shrine', 'gate', 'beacon'] = 'gate'
    collectible: Literal["crystals", "relics"] = "crystals"
    camera_mode: Literal["follow", "vertical"] = "follow"
    levels: list[LevelIR] = Field(default_factory=list, max_length=3)
    requirements: list[dict] = Field(default_factory=list)
    asset_pack: Literal["kenney_pixel_platformer"] = "kenney_pixel_platformer"
