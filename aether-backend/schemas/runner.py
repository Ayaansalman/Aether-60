"""Independent arcade movement contract; no platformer progression defaults."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class RunnerDesign(BaseModel):
    model_config = ConfigDict(extra='forbid')
    genre: Literal['runner'] = 'runner'
    title: str = Field(default='Skyline Sprint', max_length=80)
    mode: Literal['ground','flap'] = 'ground'
    theme: Literal['neon','forest','sky','ice'] = 'neon'
    player: Literal['robot','creature','cube'] = 'robot'
    endless: bool = True
    finish_distance: float = Field(default=3000, ge=500, le=50000)
    speed: float = Field(default=300, ge=180, le=400)
    max_speed: float = Field(default=440, ge=180, le=520)
    acceleration: float = Field(default=2, ge=0, le=5)
    gravity: float = Field(default=1500, ge=900, le=1800)
    jump_impulse: float = Field(default=590, ge=520, le=650)
    flap_impulse: float = Field(default=310, ge=260, le=360)
    gap_height: float = Field(default=190, ge=175, le=240)
    obstacles: list[Literal['spike','gap','laser','barrier']] = Field(default_factory=lambda:['spike','gap','laser'], min_length=1)
    scoring: Literal['distance','gaps'] = 'distance'
    unsupported: list[str] = Field(default_factory=list)
    @model_validator(mode='after')
    def physics(self):
        if self.max_speed < self.speed: raise ValueError('max_speed must be >= speed')
        if self.jump_impulse**2/(2*self.gravity)<65: raise ValueError('Jump must clear 65px obstacles')
        if self.mode=='ground' and 'barrier' in self.obstacles and self.speed*2*(max(0,self.jump_impulse**2-2*self.gravity*60)**.5)/self.gravity < 80: raise ValueError('Barrier clearance needs at least 80px of safe horizontal travel')
        if self.mode=='flap': self.scoring='gaps'
        return self

class RunnerIR(RunnerDesign):
    schema_version: Literal['2.2'] = '2.2'
    seed: int
    requirements: list[dict] = Field(default_factory=list)
