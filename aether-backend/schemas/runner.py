"""Independent arcade movement contract; no platformer progression defaults."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ChallengeDesign(BaseModel):
    """Seconds are controller time, widths are a fraction of safe jump travel."""
    model_config = ConfigDict(extra='forbid')
    patterns: list[Literal['single','rhythm','escalation','mixed','recovery','alternating','ascending','descending','corridor']] = Field(default_factory=lambda:['single','rhythm','escalation','mixed','recovery'], min_length=1, max_length=9)
    recovery: float = Field(default=.4, ge=.10, le=1.8)
    spacing: float = Field(default=1.5, ge=.8, le=2.8)
    precision: float = Field(default=.5, ge=.2, le=.85)
    transition: float = Field(default=65, ge=10, le=170)
    sequence_length: int = Field(default=4, ge=2, le=8)
    rest_every: int = Field(default=4, ge=2, le=8)

PROFILES = {
    'easy': dict(speed=210,max_speed=280,acceleration=.5,gap_height=240,challenge=dict(recovery=.9,spacing=2.1,precision=.3,transition=30,sequence_length=3,rest_every=2)),
    'medium': dict(speed=280,max_speed=370,acceleration=1,gap_height=190,challenge=dict(recovery=.4,spacing=1.5,precision=.5,transition=65,sequence_length=4,rest_every=4)),
    'hard': dict(speed=340,max_speed=440,acceleration=1.6,gap_height=145,challenge=dict(recovery=.22,spacing=1.2,precision=.68,transition=110,sequence_length=5,rest_every=5)),
    'extreme': dict(speed=390,max_speed=500,acceleration=2,gap_height=112,challenge=dict(recovery=.1,spacing=.95,precision=.82,transition=155,sequence_length=6,rest_every=6)),
}

class RunnerDesign(BaseModel):
    model_config = ConfigDict(extra='forbid')
    genre: Literal['runner'] = 'runner'
    title: str = Field(default='Skyline Sprint', max_length=80)
    mode: Literal['ground','flap'] = 'ground'
    theme: Literal['neon','forest','factory','sky','ice'] = 'neon'
    player: Literal['robot','creature','bird','cube'] = 'robot'
    visual_style: Literal['pixel'] = 'pixel'
    difficulty: Literal['easy','medium','hard','extreme'] = 'medium'
    progression: Literal['stable','gradual','surge'] = 'gradual'
    challenge: ChallengeDesign = Field(default_factory=ChallengeDesign)
    exclusions: list[Literal['spike','gap','laser','barrier']] = Field(default_factory=list)
    endless: bool = True
    finish_distance: float = Field(default=3000, ge=500, le=50000)
    speed: float = Field(default=280, ge=180, le=400)
    max_speed: float = Field(default=370, ge=180, le=520)
    acceleration: float = Field(default=1, ge=0, le=5)
    gravity: float = Field(default=1500, ge=900, le=1800)
    jump_impulse: float = Field(default=590, ge=520, le=650)
    flap_impulse: float = Field(default=310, ge=260, le=360)
    gap_height: float = Field(default=190, ge=96, le=260)
    obstacles: list[Literal['spike','gap','laser','barrier']] = Field(default_factory=lambda:['spike','gap','laser'], min_length=1)
    scoring: Literal['distance','gaps'] = 'distance'
    unsupported: list[str] = Field(default_factory=list)
    @model_validator(mode='before')
    @classmethod
    def profile_defaults(cls, value):
        if not isinstance(value,dict): return value
        data=dict(value)
        # Profiles fill omissions only. Model-authored tuning is never overwritten.
        profile=PROFILES.get(data.get('difficulty','medium'),PROFILES['medium'])
        for key,val in profile.items():
            if key!='challenge':data.setdefault(key,val)
        supplied=data.get('challenge',{})
        if isinstance(supplied,ChallengeDesign):supplied=supplied.model_dump(exclude_unset=True)
        data['challenge']={**profile['challenge'],**supplied}
        if data.get('mode')=='flap':
            challenge=dict(data.get('challenge',{}))
            challenge.setdefault('patterns',['single','alternating','ascending','descending','corridor','recovery'])
            data['challenge']=challenge
        if data.get('progression')=='stable':data['acceleration']=0
        return data
    @model_validator(mode='after')
    def physics(self):
        if self.max_speed < self.speed: raise ValueError('max_speed must be >= speed')
        if self.jump_impulse**2/(2*self.gravity)<65: raise ValueError('Jump must clear 65px obstacles')
        if self.mode=='flap': self.scoring='gaps'
        self.obstacles=[o for o in dict.fromkeys(self.obstacles) if o not in self.exclusions]
        if not self.obstacles:raise ValueError('At least one permitted obstacle family is required')
        if self.mode=='ground' and 'barrier' in self.obstacles and self.speed*2*(max(0,self.jump_impulse**2-2*self.gravity*60)**.5)/self.gravity < 80: raise ValueError('Barrier clearance needs at least 80px of safe horizontal travel')
        if self.mode=='flap' and 'gap' in self.exclusions:raise ValueError('Flap survival requires passages; excluding gaps contradicts this control mode')
        allowed={'single','rhythm','escalation','mixed','recovery'} if self.mode=='ground' else {'single','alternating','ascending','descending','corridor','recovery'}
        if not set(self.challenge.patterns)<=allowed:raise ValueError('Challenge pattern incompatible with control mode')
        # Repeated flaps can hover with this peak-to-trough excursion, plus collision size.
        if self.mode=='flap' and self.gap_height < 28+self.flap_impulse**2/(2*self.gravity)+18:
            raise ValueError('Gap too small for a bounded flap cycle and collision margin')
        return self

class RunnerIR(RunnerDesign):
    schema_version: Literal['2.2'] = '2.2'
    seed: int
    requirements: list[dict] = Field(default_factory=list)
