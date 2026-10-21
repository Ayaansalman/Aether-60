"""Adventure contracts are separate from platformer physics and section geometry."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.assets import AdventureArt


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Dialogue(Contract):
    greeting: list[str] = Field(default_factory=lambda: ['Welcome, traveler.'], min_length=1, max_length=4)
    active: list[str] = Field(default_factory=lambda: ['Your journey is still ahead.'], min_length=1, max_length=4)
    completed: list[str] = Field(default_factory=lambda: ['Thank you for your help!'], min_length=1, max_length=4)


class BiomeRegion(Contract):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    name: str = Field(max_length=60)
    biome: Literal['forest','snow','frozen_lake','icy_ruins']
    x: int = Field(ge=1,le=44)
    y: int = Field(ge=1,le=28)
    width: int = Field(ge=3,le=46)
    height: int = Field(ge=3,le=30)
    slippery: bool = False
    @model_validator(mode='after')
    def bounds(self):
        if self.x+self.width>47 or self.y+self.height>31: raise ValueError('Biome exceeds 48x32 map interior')
        return self


class Actor(Contract):
    region: str | None = None
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    kind: Literal['npc', 'item', 'door', 'switch', 'enemy', 'landmark', 'treasure']
    name: str = Field(min_length=1, max_length=60)
    area: int = Field(default=0, ge=0, le=2)
    role: str = Field(default='', max_length=80)
    item: str = Field(default='', max_length=40)
    quantity: int = Field(default=1, ge=1, le=10)
    requires: list[str] = Field(default_factory=list, max_length=5)
    behavior: Literal['patrol', 'chase'] = 'chase'
    dialogue: Dialogue = Field(default_factory=Dialogue)


class Goal(Contract):
    kind: Literal['talk', 'collect', 'deliver', 'explore', 'defeat', 'activate', 'unlock']
    target: str
    count: int = Field(default=1, ge=1, le=10)
    text: str = Field(min_length=1, max_length=140)
    item: str = Field(default='', max_length=40)
    delivery_items: dict[str, int] = Field(default_factory=dict, max_length=10)


class AreaDesign(Contract):
    regions: list[BiomeRegion] = Field(default_factory=list,max_length=8)
    name: str = Field(min_length=1, max_length=60)
    environment: Literal['village', 'forest', 'ruins', 'dungeon', 'cave']


class AdventureDesign(Contract):
    genre: Literal['adventure'] = 'adventure'
    title: str = Field(min_length=1, max_length=70)
    premise: str = Field(max_length=500)
    theme: Literal['woodland', 'dark', 'fantasy'] = 'woodland'
    art_style: str = Field(default='auto',pattern=r'^[a-z_]{1,40}$')
    areas: list[AreaDesign] = Field(min_length=1, max_length=3)
    actors: list[Actor] = Field(min_length=1, max_length=32)
    quests: list[Goal] = Field(min_length=1, max_length=16)
    combat: bool = False
    unsupported: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def references(self):
        actors = {a.id: a for a in self.actors}
        if len(actors) != len(self.actors):
            raise ValueError('Duplicate actor IDs')
        for area in self.areas:
            if len({r.id for r in area.regions})!=len(area.regions): raise ValueError('Duplicate region IDs')
        for a in self.actors:
            if a.region and (a.area>=len(self.areas) or a.region not in {r.id for r in self.areas[a.area].regions}): raise ValueError('Actor references missing biome')
        items = {a.item for a in self.actors if a.kind == 'item'}
        expected = {'talk': ['npc'], 'deliver': ['npc'], 'collect': ['item', 'treasure'], 'explore': ['landmark'],
                    'defeat': ['enemy'], 'activate': ['switch'], 'unlock': ['door']}
        for a in self.actors:
            if a.area >= len(self.areas):
                raise ValueError('Actor references nonexistent area')
            if a.kind == 'item' and not a.item:
                raise ValueError('Items need an inventory ID')
            if a.kind == 'enemy' and not self.combat:
                raise ValueError('Peaceful design contains enemies')
            for ref in a.requires:
                if ref not in items and (ref not in actors or actors[ref].kind != 'switch'):
                    raise ValueError('Door requires an unavailable item or switch')
        for q in self.quests:
            if q.target not in actors or actors[q.target].kind not in expected[q.kind]:
                raise ValueError('Quest target does not support this event')
            a = actors[q.target]
            if q.kind not in ('collect','deliver') and q.count != 1:
                raise ValueError('Non-collection goals target one explicit actor')
            if q.kind == 'deliver':
                for item,count in (q.delivery_items or {q.item:q.count}).items():
                    if item not in items or count<1 or count>10 or sum(x.quantity for x in self.actors if x.kind=='item' and x.item==item)<count:
                        raise ValueError('Delivery quantity unavailable')
            if q.kind == 'collect' and (a.quantity < q.count or q.count != 1 and a.kind == 'treasure'):
                raise ValueError('Collection quantity unavailable')
        # Monotonic area progression: all objectives in an earlier area must precede departure.
        if [actors[q.target].area for q in self.quests] != sorted(actors[q.target].area for q in self.quests):
            raise ValueError('Quest sequence must follow area order')
        if {actors[q.target].area for q in self.quests} != set(range(len(self.areas))):
            raise ValueError('Every area needs at least one objective')
        for area in range(len(self.areas)):
            if sum(a.kind=='door' and a.area==area for a in self.actors)>1:
                raise ValueError('Initial adventure adapter supports one sealed passage per area')
        return self


class PlacedActor(Actor):
    x: int
    y: int
    pickups: list[dict[str, int]] = Field(default_factory=list)


class AreaIR(AreaDesign):
    width: int
    height: int
    tiles: list[list[int]]
    spawn: dict[str, int]
    exit: dict[str, int]
    actors: list[PlacedActor]
    zones: list[dict] = Field(default_factory=list)
    trees: list[dict[str, int]] = Field(default_factory=list)
    buildings: list[dict[str, int]] = Field(default_factory=list)


class AdventureIR(Contract):
    schema_version: Literal['2.1'] = '2.1'
    genre: Literal['adventure'] = 'adventure'
    title: str
    premise: str
    theme: str
    seed: int
    tile_size: Literal[32] = 32
    combat: bool
    art: AdventureArt | None = None
    areas: list[AreaIR]
    quests: list[Goal]
    unsupported: list[str] = Field(default_factory=list)
    requirements: list[dict] = Field(default_factory=list)
