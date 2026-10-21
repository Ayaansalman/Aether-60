import type {GameIR} from '../gameir';
export type SurvivalStream={spawn_interval_ms:number;selection:'random';max_active:number;safe_radius:number;warning_ms:number;chaser_lifetime_ms:number;shooter_shots:number;shot_interval_ms:number;expire_after_burst:true;bullet_speed:number;bullet_lifetime_ms:number};
export type SurvivalIR=GameIR&{schema_version:'2.3';survival_stream:SurvivalStream;requirements:{source:string;status:string}[];unsupported:string[]};
/** Emit one aimed bullet per interval, never a burst of catch-up bullets after a pause. */
export function emitterStep(shots:number,lastAt:number,now:number,config:Pick<SurvivalStream,'shooter_shots'|'shot_interval_ms'>){
 const fire=shots<config.shooter_shots&&now-lastAt>=config.shot_interval_ms;
 return {fire,shots:shots+(fire?1:0),lastAt:fire?now:lastAt,expired:shots+(fire?1:0)>=config.shooter_shots};
}
export function safeSpawn(random:()=>number,width:number,height:number,player:{x:number;y:number},radius:number){
 for(let i=0;i<100;i++){const point={x:32+random()*(width-64),y:125+random()*(height-160)};if(Math.hypot(point.x-player.x,point.y-player.y)>=radius)return point;}
 return null;
}
