"""Versioned design contracts. Genre dispatch is explicit; v1 remains supported."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnemyConfig(Contract):
    health: int = Field(default=1, ge=1, le=3)
    cooldown_ms: int = Field(default=1400, ge=400, le=5000)
    telegraph_ms: int = Field(default=450, ge=150, le=1500)
    radius: int = Field(default=300, ge=80, le=500)


class Motion(Contract):
    axis: Literal['horizontal', 'vertical'] = 'horizontal'
    pattern: Literal['sine', 'ping_pong'] = 'sine'
    distance: int = Field(default=54, ge=24, le=108)
    period_ms: int = Field(default=3000, ge=2000, le=8000)


class GoalDesign(Contract):
    kind: Literal['defeat', 'activate', 'unlock', 'collect', 'survive', 'time_limit']
    count: int = Field(default=0, ge=0, le=64, description='Zero means all available targets; explicit positive counts must be achievable')
    seconds: int = Field(default=30, ge=1, le=180)
    enemy_behavior: Literal['patrol','chase','shooter','turret','ambusher'] | None = None

    @model_validator(mode='after')
    def valid_selector(self):
        if self.enemy_behavior is not None and self.kind != 'defeat':
            raise ValueError('Enemy behavior selectors are only valid for defeat objectives')
        return self


class Goal(GoalDesign):
    id: str = Field(min_length=1, max_length=80)
    targets: list[str] = Field(default_factory=list, max_length=256)


class InteractionDesign(Contract):
    trigger: Literal['interact', 'touch', 'pressure', 'proximity', 'projectile'] = 'interact'
    section: int = Field(default=0, ge=0, le=13)
    door_section: int = Field(default=1, ge=0, le=13)


class BehaviorLink(Contract):
    sources: list[str] = Field(min_length=1, max_length=8)
    target: str = Field(min_length=1, max_length=80)
    condition: Literal['all', 'any'] = 'all'
    action: Literal['open_door'] = 'open_door'


class Section(Contract):
    kind: Literal["meadow", "ruins", "factory", "ascent", "gauntlet", "cavern", "terraces", "bridge"]
    length: int = Field(default=6, ge=4, le=10)
    elevation: int = Field(default=0, ge=-1, le=2)
    gap: int = Field(default=2, ge=1, le=3)
    enemies: bool = True
    hazards: bool = False
    encounter: Literal["patrol", "chase", "shooter", "turret", "ambusher"] = "patrol"
    ai: EnemyConfig = Field(default_factory=EnemyConfig)
    challenge: Literal['traversal', 'precision', 'combat', 'hazards', 'exploration', 'moving'] = 'traversal'


class RequestedFeature(Contract):
    source: str = Field(min_length=1, max_length=300)
    capability: Literal['ice_environment', 'forest_environment', 'factory_environment', 'slippery',
                        'falling_icicles', 'exit_indicator', 'collectibles', 'patrol', 'robots', 'chase',
                        'ranged', 'moving_platforms', 'timed_hazards', 'checkpoints', 'multiple_levels',
                        'double_jump', 'dash', 'switches', 'pressure_plates', 'projectile_switches',
                        'combat_objective', 'timed_objective', 'survival_objective', 'turret', 'ambusher', 'player_projectiles', 'unsupported']
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
    platform_motion: Motion | None = None
    player_attack: Literal['stomp', 'projectile'] | None = None
    interactions: list[InteractionDesign] | None = Field(default=None, max_length=4)
    objectives: list[GoalDesign] | None = Field(default=None, max_length=6)
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
    platform_motion: Motion = Field(default_factory=Motion)
    player_attack: Literal['stomp', 'projectile'] = 'stomp'
    interactions: list[InteractionDesign] = Field(default_factory=list, max_length=4)
    objectives: list[GoalDesign] = Field(default_factory=list, max_length=6)
    campaign_objectives: list[GoalDesign] = Field(default_factory=list, max_length=6)
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
    motion: Motion = Field(default_factory=Motion)


class Entity(Contract):
    id: str = Field(default='', max_length=80)
    x: float
    y: float
    kind: Literal["crystal", "enemy", "spikes", "checkpoint", "exit", "icicle", "timed_hazard", 'switch', 'pressure_plate', 'door']
    platform: int
    behavior: Literal["patrol", "chase", "shooter", 'turret', 'ambusher'] = "patrol"
    ai: EnemyConfig = Field(default_factory=EnemyConfig)
    activation: Literal['interact', 'touch', 'pressure', 'proximity', 'projectile'] = 'interact'
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
    goals: list[Goal] = Field(default_factory=list, max_length=10)
    links: list[BehaviorLink] = Field(default_factory=list, max_length=4)
    player_attack: Literal['stomp', 'projectile'] | None = None

    @model_validator(mode='after')
    def gameplay_references(self):
        identified = [e.id for e in self.entities if e.id]
        if len(identified) != len(set(identified)):
            raise ValueError('Entity IDs must be unique within a level')
        entities = {e.id:e for e in self.entities if e.id}
        for link in self.links:
            if link.target not in entities or entities[link.target].kind != 'door':
                raise ValueError('Behavior links must target an existing door')
            if any(source not in entities or entities[source].kind not in ('switch', 'pressure_plate') for source in link.sources):
                raise ValueError('Behavior links must use existing switches or plates')
            if any(entities[source].platform>entities[link.target].platform or
                   entities[source].platform==entities[link.target].platform and entities[source].x>=entities[link.target].x for source in link.sources):
                raise ValueError('Door activation sources must be reachable before their door')
        if len({goal.id for goal in self.goals})!=len(self.goals):
            raise ValueError('Objective IDs must be unique')
        for goal in self.goals:
            if len(set(goal.targets))!=len(goal.targets): raise ValueError('Objective targets must be unique')
            if any(target not in entities for target in goal.targets):
                raise ValueError('Objective target does not exist in this level')
            kinds = {'defeat':('enemy',), 'activate':('switch','pressure_plate'), 'unlock':('door',), 'collect':('crystal',)}.get(goal.kind)
            if kinds and (not goal.targets or goal.count > len(set(goal.targets)) or any(entities[target].kind not in kinds for target in goal.targets)):
                raise ValueError('Objective targets must match their kind and required count')
        if any(e.kind=='door' and e.id not in {link.target for link in self.links} for e in self.entities):
            raise ValueError('Every door requires a registered activation link')
        if any(e.activation=='projectile' and e.kind=='switch' for e in self.entities) and self.player_attack != 'projectile':
            raise ValueError('Projectile switches require player_attack=projectile')
        return self


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
    campaign_goals: list[Goal] = Field(default_factory=list, max_length=6)
    requirements: list[dict] = Field(default_factory=list)
    asset_pack: Literal["kenney_pixel_platformer"] = "kenney_pixel_platformer"

    @model_validator(mode='after')
    def campaign_references(self):
        entities = [entity for level in (self.levels or [self]) for entity in level.entities if entity.id]
        if len({entity.id for entity in entities}) != len(entities):
            raise ValueError('Campaign entity IDs must be unique across levels')
        by_id = {entity.id:entity for entity in entities}
        for goal in self.campaign_goals:
            if len(set(goal.targets))!=len(goal.targets): raise ValueError('Campaign objective targets must be unique')
            kinds = {'defeat':('enemy',), 'activate':('switch','pressure_plate'), 'unlock':('door',), 'collect':('crystal',)}.get(goal.kind)
            if kinds and (not goal.targets or goal.count > len(set(goal.targets)) or any(target not in by_id or by_id[target].kind not in kinds for target in goal.targets)):
                raise ValueError('Campaign objectives must reference enough existing matching targets')
        return self
