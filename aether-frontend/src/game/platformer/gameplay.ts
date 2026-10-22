/** Registered gameplay components. No interpreter, dynamic code or Phaser dependencies. */
import type { BehaviorLink, Goal, Motion, EnemyConfig, Entity } from './types';
import { enemyDecision } from './behaviors.ts';

export type Progress = Record<'defeat' | 'activate' | 'unlock' | 'collect', string[]>;
export const emptyProgress = (): Progress => ({defeat:[], activate:[], unlock:[], collect:[]});
export class Gameplay {
  progress: Progress;
  links: BehaviorLink[];
  constructor(links: BehaviorLink[], progress?: Progress) {
    this.links = links;
    this.progress = structuredClone(progress || emptyProgress());
  }
  emit(kind: keyof Progress, id: string): string[] {
    if (!id || this.progress[kind].includes(id)) return [];
    this.progress[kind].push(id);
    const opened: string[] = [];
    for (const link of this.links) {
      const active = link.sources.map(source => this.progress.activate.includes(source));
      if ((link.condition === 'all' ? active.every(Boolean) : active.some(Boolean)) && !this.progress.unlock.includes(link.target)) {
        this.progress.unlock.push(link.target); opened.push(link.target);
      }
    }
    return opened;
  }
  conditions(goals: Goal[], elapsed: number) {
    return goals.map(goal => {
      const amount = goal.kind === 'survive' || goal.kind === 'time_limit' ? elapsed / 1000 :
        goal.targets.filter(id => this.progress[goal.kind as keyof Progress].includes(id)).length;
      const needed = goal.kind === 'survive' || goal.kind === 'time_limit' ? goal.seconds : goal.count || goal.targets.length;
      const failed = goal.kind === 'time_limit' && amount > needed;
      return {id:goal.id, kind:goal.kind, amount, needed, complete:goal.kind === 'time_limit' ? !failed : amount >= needed, failed};
    });
  }
}

export function triggerReady(kind: Entity['activation'], sensors: {near:boolean; contact:boolean; grounded:boolean; interact:boolean; projectile:boolean}) {
  switch (kind) {
    case 'interact': return sensors.near && sensors.interact;
    case 'touch': return sensors.contact;
    case 'pressure': return sensors.contact && sensors.grounded;
    case 'proximity': return sensors.near;
    case 'projectile': return sensors.projectile;
    default: return false;
  }
}

export function platformPosition(x: number, y: number, motion: Motion, elapsed: number) {
  const phase = (elapsed % motion.period_ms) / motion.period_ms;
  const offset = motion.pattern === 'ping_pong' ? (1 - 4 * Math.abs(((phase+.25)%1) - .5)) * motion.distance : Math.sin(phase * Math.PI * 2) * motion.distance;
  return {x:x + (motion.axis === 'horizontal' ? offset : 0), y:y + (motion.axis === 'vertical' ? offset : 0)};
}

export type EnemyPhase = 'idle' | 'reposition' | 'windup' | 'attack' | 'recover' | 'hurt';
export interface EnemyMemory { phase: EnemyPhase; at: number; direction: number; cycle?:number }
export function enemyStep(behavior: string, memory: EnemyMemory, sensor: {x:number; y:number; low:number; high:number; playerX:number; playerY:number}, now: number, config: EnemyConfig) {
  const decision = enemyDecision(behavior, sensor.x, sensor.y, sensor.low, sensor.high, memory.direction, sensor.playerX, sensor.playerY, 0);
  const elapsed = now - memory.at, dx = sensor.playerX - sensor.x;
  const ranged = behavior === 'shooter' || behavior === 'turret', ambush = behavior === 'ambusher';
  const inRange = Math.abs(dx) <= (ambush ? Math.min(config.radius,160) : config.radius) && Math.abs(sensor.playerY-sensor.y) < 90;
  let next = {...memory, direction:decision.direction}, vx = decision.vx, fire = false;
  if (memory.phase === 'hurt') {
    vx = 0;
    if (elapsed >= 250) next = {...next, phase:ranged || ambush ? 'recover' : 'idle', at:now};
  } else if (ranged || ambush) {
    vx = 0;
    if (memory.phase === 'reposition') {
      const retreat=-memory.direction*110;
      if (elapsed>=350 || Math.abs(dx)>=160 || retreat<0&&sensor.x<=sensor.low+2 || retreat>0&&sensor.x>=sensor.high-2) next={phase:'windup',at:now,direction:Math.sign(dx)||memory.direction};
      else vx=retreat;
    } else if (memory.phase === 'windup') {
      if (elapsed >= config.telegraph_ms) { next = {...next, phase:'attack', at:now}; fire = ranged; }
    } else if (memory.phase === 'attack') {
      if (ambush && elapsed < 280) vx = memory.direction * 280;
      else next = {...next, phase:'recover', at:now};
    } else if (memory.phase === 'recover') {
      if (elapsed >= config.cooldown_ms) next = {...next, phase:'idle', at:now};
    } else if (inRange) {
      next = {phase:behavior==='shooter'&&Math.abs(dx)<120?'reposition':'windup', at:now, direction:Math.sign(dx) || memory.direction};
    }
    // Shooters create space; turrets stay anchored; ambushers commit to the telegraphed direction.
    if (behavior === 'shooter' && next.phase === 'idle' && Math.abs(sensor.playerY-sensor.y)<90 && Math.abs(dx)<config.radius+160) vx=Math.sign(dx)*85;
    if (next.phase === 'windup' || next.phase === 'attack') next.direction = memory.phase === 'idle' ? next.direction : memory.direction;
  }
  if (vx < 0 && sensor.x <= sensor.low || vx > 0 && sensor.x >= sensor.high) vx = 0;
  return {memory:next, vx, fire};
}

/** Boss cycles between a committed charge and a three-shot volley, with a readable windup. */
export function bossStep(memory:EnemyMemory,now:number,health:number,maxHealth:number,playerX:number,x:number,low:number,high:number,telegraph:number,cooldown:number,patterns:string[]=['charge','volley']) {
  const elapsed=now-memory.at;let next={...memory};let vx=0,fire=false,slam=false;
  const pattern=patterns[((memory.cycle||1)-1)%patterns.length];
  const phase2=health<=maxHealth/2;
  if(memory.phase==='hurt'){if(elapsed>=250)next={...next,phase:'recover',at:now};}
  else if(memory.phase==='idle'||memory.phase==='recover'){
    if(elapsed>=cooldown*(phase2?.7:1))next={phase:'windup',at:now,direction:Math.sign(playerX-x)||-1,cycle:(memory.cycle||0)+1};
  }else if(memory.phase==='windup'){
    if(elapsed>=telegraph){next={...next,phase:'attack',at:now};fire=pattern==='volley';slam=pattern==='slam';}
  }else if(memory.phase==='attack'){
    if(elapsed<480&&pattern==='charge')vx=memory.direction*(phase2?340:270);
    else next={...next,phase:'recover',at:now};
  }
  if(x<=low&&vx<0||x>=high&&vx>0)vx=0;
  return {memory:next,vx,fire,slam,pattern};
}
