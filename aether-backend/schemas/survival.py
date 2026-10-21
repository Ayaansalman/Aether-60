"""V2 adapter for the existing arena engine, with explicit endless and emitter contracts."""
from typing import Literal
from pydantic import Field,model_validator
from schemas.game_ir import GameIR,PlayerConfig,EnemyConfig
from schemas.platformer import Contract

class SurvivalObjective(Contract):
    type: Literal['survive_endless','survive_seconds']='survive_endless'
    target: int = Field(default=0,ge=0,le=3600)
    @model_validator(mode='after')
    def valid_duration(self):
        if self.type=='survive_endless' and self.target!=0:raise ValueError('Endless survival cannot have a finite win target')
        if self.type=='survive_seconds' and self.target<5:raise ValueError('Finite survival requires at least 5 seconds')
        return self

class SurvivalPlayer(PlayerConfig):
    move_speed: float = Field(default=220,ge=100,le=300)
    max_health: int = Field(default=3,ge=1,le=10)
    attack_mode: Literal['avoid_only']='avoid_only'

class SurvivalEnemy(EnemyConfig):
    type: Literal['chaser','shooter']
    count: Literal[1]=1
    speed: float = Field(default=80,ge=20,le=160)

class SurvivalStream(Contract):
    spawn_interval_ms: int = Field(default=1500,ge=500,le=10000)
    selection: Literal['random']='random'
    max_active: int = Field(default=18,ge=2,le=30)
    safe_radius: int = Field(default=200,ge=160,le=300)
    warning_ms: int = Field(default=500,ge=250,le=1000)
    chaser_lifetime_ms: int = Field(default=30000,ge=10000,le=60000)
    shooter_shots: int = Field(default=5,ge=1,le=30)
    shot_interval_ms: int = Field(default=1000,ge=250,le=5000)
    expire_after_burst: Literal[True]=True
    bullet_speed: int = Field(default=140,ge=80,le=250)
    bullet_lifetime_ms: int = Field(default=5000,ge=1000,le=8000)
    @model_validator(mode='after')
    def warning_precedes_first_shot(self):
        if self.warning_ms>self.shot_interval_ms:raise ValueError('Spawn warning must finish before the first shot interval')
        return self

class SurvivalDesign(GameIR):
    genre: Literal['arena_survival']='arena_survival'
    schema_version: Literal['2.3']='2.3'
    title: str = Field(default='Bulletfall Survival',min_length=1,max_length=50)
    premise: str = Field(default='Dodge enemies and bullets for as long as possible.',max_length=240)
    theme: Literal['fantasy','sci_fi','pirate','spooky','cozy']='sci_fi'
    arena_layout: Literal['open']='open'
    player: SurvivalPlayer = Field(default_factory=SurvivalPlayer)
    enemies: list[SurvivalEnemy] = Field(default_factory=lambda:[SurvivalEnemy(type='chaser'),SurvivalEnemy(type='shooter')],min_length=1,max_length=2)
    collectibles: list = Field(default_factory=list,max_length=0)
    objective: SurvivalObjective = Field(default_factory=SurvivalObjective)
    difficulty: int = Field(default=2,ge=1,le=5)
    controls: dict[str,str] = Field(default_factory=lambda:{'movement':'WASD / arrows','restart':'R'})
    survival_stream: SurvivalStream = Field(default_factory=SurvivalStream)
    unsupported: list[str] = Field(default_factory=list,max_length=20)

class SurvivalIR(SurvivalDesign):
    requirements: list[dict] = Field(default_factory=list)
