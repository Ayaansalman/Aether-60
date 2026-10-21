import type {BiomeRegion} from './types';
/** Later nested regions take priority; snow visuals alone never imply a movement effect. */
export function biomeAt(regions:BiomeRegion[],x:number,y:number){return [...regions].reverse().find(r=>x>=r.x&&x<r.x+r.width&&y>=r.y&&y<r.y+r.height);}
