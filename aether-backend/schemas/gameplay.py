"""Controlled behavior components; no model-authored code or new renderer family."""
from typing import Literal
import math
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Component(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AttackSequence(Component):
    interval_ms: int = Field(default=1000, ge=250, le=10000)
    shots: int = Field(default=5, ge=1, le=50)
    windup_ms: int = Field(default=350, ge=150, le=2000)
    projectile_speed: int = Field(default=180, ge=60, le=500)
    after: Literal['despawn', 'repeat'] = 'despawn'

    @model_validator(mode='after')
    def readable_warning(self):
        if self.windup_ms > self.interval_ms:raise ValueError('Shot windup must fit inside the shot interval')
        return self


class EnemyArchetype(Component):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    name: str = Field(min_length=1, max_length=60)
    behavior: Literal['chase', 'shooter', 'patrol']
    speed: int = Field(default=65, ge=0, le=200)
    health: int = Field(default=2, ge=1, le=30)
    attack: AttackSequence | None = None

    @model_validator(mode='after')
    def compatible(self):
        if (self.behavior == 'shooter') != (self.attack is not None):
            raise ValueError('Only shooter behavior requires an attack sequence')
        return self


class SpawnRule(Component):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    archetypes: list[str] = Field(min_length=1, max_length=8)
    interval_ms: int = Field(default=1800, ge=500, le=15000)
    max_alive: int = Field(default=16, ge=1, le=40)
    safe_radius: int = Field(default=220, ge=128, le=400)


class Gameplay(Component):
    """Relations: spawn timer→random archetype; attack counter→despawn; health→loss."""
    feedback: Literal['subtle','clear'] = 'clear'
    health: int = Field(default=5, ge=1, le=20)
    invulnerability_ms: int = Field(default=1000, ge=250, le=2000)
    player_attack: bool = False
    outcome: Literal['quests', 'endless', 'survive'] = 'quests'
    duration_seconds: int | None = Field(default=None, ge=5, le=600)
    scoring: Literal['none', 'survival_time'] = 'none'
    archetypes: list[EnemyArchetype] = Field(default_factory=list, max_length=8)
    spawns: list[SpawnRule] = Field(default_factory=list, max_length=4)

    @model_validator(mode='after')
    def dependencies(self):
        ids = {a.id for a in self.archetypes}
        if len(ids) != len(self.archetypes) or len({s.id for s in self.spawns}) != len(self.spawns):
            raise ValueError('Behavior component IDs must be unique')
        if any(not set(s.archetypes) <= ids for s in self.spawns):
            raise ValueError('Spawn rule references a missing enemy archetype')
        referenced={ref for s in self.spawns for ref in s.archetypes}
        if ids != referenced:raise ValueError('Every enemy archetype must be referenced by a spawn rule')
        if sum(s.max_alive for s in self.spawns)>64:raise ValueError('Combined live enemy budget exceeds 64')
        by_id={a.id:a for a in self.archetypes}
        bullets=0
        for s in self.spawns:
            shots=max((min(by_id[ref].attack.shots,math.ceil(6000/by_id[ref].attack.interval_ms)+1) for ref in s.archetypes if by_id[ref].attack),default=0)
            bullets+=(s.max_alive+math.ceil(6000/s.interval_ms))*shots
        if bullets>240:raise ValueError('Projectile concurrency budget exceeds 240; reduce spawn cap or increase intervals')
        if (self.outcome == 'survive') != (self.duration_seconds is not None):
            raise ValueError('outcome=survive requires a positive duration_seconds; outcome=endless or quests requires duration_seconds=null (never 0)')
        return self
