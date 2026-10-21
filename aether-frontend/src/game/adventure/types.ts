export type BiomeRegion={id:string;name:string;biome:'forest'|'snow'|'frozen_lake'|'icy_ruins';x:number;y:number;width:number;height:number;slippery:boolean};
export type Dialogue = { greeting: string[]; active: string[]; completed: string[] };
export type Actor = {
  id: string; kind: 'npc'|'item'|'door'|'switch'|'enemy'|'landmark'|'treasure';
  name: string; role: string; item: string; quantity: number; requires: string[];
  behavior: 'patrol'|'chase'; dialogue: Dialogue; x: number; y: number; area: number; pickups:{x:number;y:number}[];
};
export type Goal = { kind: 'talk'|'collect'|'deliver'|'explore'|'defeat'|'activate'|'unlock'; target: string; count: number; text: string; item: string; delivery_items?:Record<string,number> };
export type Area = { regions?:BiomeRegion[]; name: string; environment: string; width: number; height: number; tiles: number[][]; spawn: {x:number;y:number}; exit:{x:number;y:number}; actors: Actor[]; zones?:{name:string;x:number;y:number}[]; trees?:{x:number;y:number}[]; buildings?:{x:number;y:number;variant:number}[] };
export type AdventureIR = {
  schema_version:'2.1'; genre:'adventure'; title:string; premise:string; theme:string; seed:number;
  tile_size:32; combat:boolean; areas:Area[]; quests:Goal[]; unsupported:string[];
  art?:AdventureArt|null;
  requirements:{source:string;status:string}[];
};
export type AdventureUI = {objective:string;inventory:string;dialogue:string;health:number;progress:string};
export type TextureAsset={id:string;url:string;pack_id:string;style_family:string;category:string;width:number;height:number;frame_width:number;frame_height:number;scale:number;
  animations:Record<string,Record<string,number[]>>;body:{width:number;height:number;offset_x:number;offset_y:number}|null};
export type AssetVisual={asset:string;frame:number;open_frame?:number|null};
export type AdventureArt={pack_id:string;style_family:string;catalog_version:string;source:string;license:string;license_files:string[];selection_reason:string;
  player:string;actors:Record<string,string>;assets:Record<string,TextureAsset>;roles:Record<string,AssetVisual>;
  terrain:{texture:string;ground:number[];path:number;edges:Record<string,number>;solid:number;decoration:number;indoor_ground:number;wall:number;debris:number;indoor_details?:number[];buildings:number[][]}};
