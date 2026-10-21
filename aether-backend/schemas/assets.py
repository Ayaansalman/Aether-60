"""Renderer-independent, resolved asset references; no model-authored URLs."""
from pydantic import BaseModel, Field, model_validator


class TextureAsset(BaseModel):
    id: str
    pack_id: str
    style_family: str
    category: str
    url: str = Field(pattern=r'^/assets/adventure/[a-zA-Z0-9_./-]+$')
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_width: int = Field(gt=0)
    frame_height: int = Field(gt=0)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    license: str
    redistributable: bool
    scale: float = Field(gt=0,le=4)
    animations: dict[str,dict[str,list[int]]] = Field(default_factory=dict)
    body: dict[str,int] | None = None
    source_path: str


class AssetVisual(BaseModel):
    asset: str
    frame: int = Field(default=0,ge=0)
    open_frame: int | None = Field(default=None,ge=0)


class TerrainArt(BaseModel):
    texture: str
    ground: list[int]
    path: int
    edges: dict[str,int]
    solid: int
    decoration: int
    indoor_ground: int
    wall: int
    debris: int
    indoor_details: list[int] = Field(default_factory=list)
    buildings: list[list[int]]


class AdventureArt(BaseModel):
    pack_id: str
    style_family: str
    catalog_version: str
    source: str
    license: str
    license_files: list[str]
    selection_reason: str
    player: str
    actors: dict[str,str]
    assets: dict[str,TextureAsset]
    roles: dict[str,AssetVisual]
    terrain: TerrainArt

    @model_validator(mode='after')
    def coherent(self):
        if self.license!='CC0-1.0':raise ValueError('Redistribution eligibility requires explicit review')
        if self.player not in self.assets or self.terrain.texture not in self.assets:
            raise ValueError('Required asset dependency missing')
        for asset in self.assets.values():
            if asset.style_family!=self.style_family or asset.pack_id!=self.pack_id:
                raise ValueError('Mixed visual families are not supported')
            if not asset.redistributable or asset.license!='CC0-1.0':
                raise ValueError('Asset not eligible for resource redistribution')
        if any(id not in self.assets for id in self.actors.values()):raise ValueError('Unknown actor asset')
        for role in self.roles.values():
            if role.asset not in self.assets:raise ValueError('Unknown role asset')
        return self
