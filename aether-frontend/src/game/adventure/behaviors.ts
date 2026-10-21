/** Deterministic, bounded behavior scheduler consumed by the existing Phaser scene. */
export type AttackSequence={interval_ms:number;shots:number;windup_ms:number;projectile_speed:number;after:'despawn'|'repeat'};
export type EnemyArchetype={id:string;name:string;behavior:'chase'|'shooter'|'patrol';speed:number;health:number;attack:AttackSequence|null};
export type SpawnRule={id:string;archetypes:string[];interval_ms:number;max_alive:number;safe_radius:number};
export type Gameplay={feedback?:'subtle'|'clear';health:number;invulnerability_ms:number;player_attack:boolean;outcome:'quests'|'endless'|'survive';duration_seconds:number|null;scoring:'none'|'survival_time';archetypes:EnemyArchetype[];spawns:SpawnRule[]};
export type BehaviorEnemy={id:string;rule:string;archetype:EnemyArchetype;x:number;y:number;shots:number;nextShot:number;warned:boolean};
export type BehaviorEvent={type:'spawn'|'windup'|'shot'|'despawn';id:string;at:number;shot?:number;distance?:number};

export class BehaviorWorld {
  elapsed=0;
  enemies=new Map<string,BehaviorEnemy>();
  events:BehaviorEvent[]=[];
  totalShots=0;
  completedSequences=0;
  private nextSpawn:number[];
  private sequence=0;
  private rng:number;
  config:Gameplay;
  positions:{x:number;y:number}[];
  constructor(config:Gameplay,seed:number,positions:{x:number;y:number}[]) {
    this.config=config;this.positions=positions;this.rng=seed>>>0;this.nextSpawn=config.spawns.map(s=>s.interval_ms);
  }
  private random(){this.rng=(Math.imul(this.rng,1664525)+1013904223)>>>0;return this.rng/4294967296;}
  remove(id:string){this.enemies.delete(id);}
  advance(ms:number,player:{x:number;y:number},emit:(event:BehaviorEvent,enemy:BehaviorEnemy)=>void){
    this.elapsed+=Math.max(0,ms);
    const send=(event:BehaviorEvent,enemy:BehaviorEnemy)=>{this.events.push(event);if(this.events.length>100)this.events.shift();emit(event,enemy);};
    this.config.spawns.forEach((rule,index)=>{
      if(this.elapsed<this.nextSpawn[index])return;
      this.nextSpawn[index]=this.elapsed+rule.interval_ms;
      if([...this.enemies.values()].filter(e=>e.rule===rule.id).length>=rule.max_alive)return;
      const valid=this.positions.filter(p=>Math.hypot(p.x-player.x,p.y-player.y)>=rule.safe_radius && [...this.enemies.values()].every(e=>Math.hypot(e.x-p.x,e.y-p.y)>48));
      if(!valid.length)return;
      const p=valid[Math.floor(this.random()*valid.length)];
      const choice=rule.archetypes[Math.floor(this.random()*rule.archetypes.length)];
      const archetype=this.config.archetypes.find(a=>a.id===choice)!;
      const enemy:BehaviorEnemy={id:`spawn_${++this.sequence}`,rule:rule.id,archetype,...p,shots:0,nextShot:this.elapsed+(archetype.attack?.windup_ms||0),warned:false};
      this.enemies.set(enemy.id,enemy);send({type:'spawn',id:enemy.id,at:this.elapsed,distance:Math.hypot(p.x-player.x,p.y-player.y)},enemy);
    });
    for(const enemy of this.enemies.values()){
      const attack=enemy.archetype.attack;if(!attack)continue;
      if(!enemy.warned&&this.elapsed>=enemy.nextShot-attack.windup_ms){enemy.warned=true;send({type:'windup',id:enemy.id,at:this.elapsed},enemy);}
      while(this.elapsed+1e-6>=enemy.nextShot){
        enemy.shots++;this.totalShots++;
        send({type:'shot',id:enemy.id,at:enemy.nextShot,shot:enemy.shots},enemy);
        enemy.nextShot+=attack.interval_ms;enemy.warned=false;
        if(enemy.shots===attack.shots){
          this.completedSequences++;
          if(attack.after==='despawn'){this.enemies.delete(enemy.id);send({type:'despawn',id:enemy.id,at:enemy.nextShot-attack.interval_ms},enemy);break;}
          enemy.shots=0;
        }
      }
    }
  }
}

export function spawnPositions(area:{width:number;height:number;tiles:number[][];spawn:{x:number;y:number};actors:{kind:string;x:number;y:number}[]}){
  const blocked=new Set(area.actors.filter(a=>a.kind==='door').map(a=>`${a.x},${a.y}`));
  const open=(x:number,y:number)=>x>0&&y>0&&x<area.width-1&&y<area.height-1&&![1,4].includes(area.tiles[y][x])&&area.tiles[y][x]<10&&!blocked.has(`${x},${y}`);
  const seen=new Set<string>(),todo=[area.spawn];
  for(let i=0;i<todo.length;i++){
    const {x,y}=todo[i],key=`${x},${y}`;if(seen.has(key)||!open(x,y))continue;seen.add(key);
    for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]])if(!seen.has(`${x+dx},${y+dy}`))todo.push({x:x+dx,y:y+dy});
  }
  return [...seen].map(key=>{const [x,y]=key.split(',').map(Number);return {x,y};}).filter(p=>[-1,0,1].every(dy=>[-1,0,1].every(dx=>open(p.x+dx,p.y+dy)))&&area.actors.every(a=>Math.hypot(a.x-p.x,a.y-p.y)>2)).map(p=>({x:p.x*32+16,y:p.y*32+16}));
}
