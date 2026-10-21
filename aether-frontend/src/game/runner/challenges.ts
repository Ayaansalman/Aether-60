import type {RunnerWorld, RunnerIR, Obstacle} from './world.ts';

export function jumpEnvelope(s:RunnerIR, height=40) {
  // Circle collision uses player bottom. 14px radius + 14px floor offset cancel.
  const apex=s.jump_impulse**2/(2*s.gravity);
  const window=2*Math.sqrt(Math.max(0,s.jump_impulse**2-2*s.gravity*(height+4)))/s.gravity;
  return {apex,flight:2*s.jump_impulse/s.gravity,clearWidth:s.speed*window-28};
}
export type FlightState={y:number;v:number};
/** Bounded beam search, same semi-implicit 120Hz integrator and 14px collider.
 * Flap/no-flap every 1/30s, sampled at min/max speed. Survivors carry into the
 * next gate so validation cannot reset velocity or teleport to a gap center. */
export function reachableGate(s:RunnerIR, states:FlightState[], travel:number, gate:Obstacle, speed:number):FlightState[] {
  const duration=travel/speed, steps=Math.ceil(duration*30), dt=duration/steps/4;
  let beam=states;
  for(let i=0;i<steps;i++){
    const candidates=new Map<string,FlightState>();
    for(const state of beam)for(const flap of [false,true]){
      let y=state.y,v=flap?-s.flap_impulse:state.v,valid=true;
      for(let j=0;j<4;j++){
        v+=s.gravity*dt;y+=v*dt;
        const remaining=travel-speed*((i*4+j+1)*dt);
        const inside=remaining<=gate.width+28;
        if(y<18||y>522||(inside&&(y-14<gate.center-gate.gap/2+3||y+14>gate.center+gate.gap/2-3))){valid=false;break;}
      }
      if(valid)candidates.set(`${Math.round(y/5)},${Math.round(v/35)}`,{y,v});
    }
    // Keep diverse velocities and positions rather than only the center-most state.
    beam=[...candidates.values()];
    if(beam.length>64){beam.sort((a,b)=>(Math.abs(a.y-gate.center)+Math.abs(a.v)*.05)-(Math.abs(b.y-gate.center)+Math.abs(b.v)*.05));beam=beam.filter((_,i)=>i%Math.ceil(beam.length/64)===0).slice(0,64);}
    if(!beam.length)return [];
  }
  return beam;
}

/** Short motif phrases, seeded variation, explicit rests, and finite termination. */
export class ChallengeStream {
  world:RunnerWorld;pending:Obstacle[]=[];section=0;previous='';lastEnd=180;bag:string[]=[];
  low:FlightState[]=[{y:250,v:0}];high:FlightState[]=[{y:250,v:0}];repairs=0;
  constructor(world:RunnerWorld){this.world=world;}
  populate(){
    const w=this.world;
    while(w.nextX<w.distance+1250){
      if(!w.spec.endless&&w.nextX>w.spec.finish_distance+180)break;
      if(!this.pending.length)this.phrase();
      const o=this.pending.shift()!;
      w.obstacles.push(o);
      w.nextX=this.pending[0]?.x??o.x+o.width+this.restDistance(o);
    }
  }
  restDistance(o:Obstacle){
    const w=this.world,c=w.spec.challenge!;
    const recovery=o.pattern==='recovery'?1.7:1;
    return w.spec.max_speed*(w.spec.mode==='ground'?jumpEnvelope(w.spec).flight+c.recovery*recovery:c.spacing*recovery);
  }
  phrase(){
    const w=this.world,s=w.spec,c=s.challenge!,r=()=>w.random();
    const progress=s.progression==='stable'?1:Math.min(1,.35+w.nextX/18000);
    if(!this.bag.length){
      this.bag=[...new Set(c.patterns.filter(p=>p!=='recovery'))];
      if(!this.bag.length)this.bag=['recovery'];
      for(let i=this.bag.length-1;i>0;i--){const j=Math.floor(r()*(i+1));[this.bag[i],this.bag[j]]=[this.bag[j],this.bag[i]];}
      if(this.bag.length>1&&this.bag[0]===this.previous)this.bag.push(this.bag.shift()!);
    }
    const pattern=this.section>0&&this.section%c.rest_every===0&&c.patterns.includes('recovery')?'recovery':this.bag.shift()!;
    this.previous=pattern;
    const count=pattern==='single'?1:pattern==='recovery'?2:Math.min(8,Math.max(2,c.sequence_length-1+Math.floor(r()*3)));
    let x=w.nextX;
    for(let i=0;i<count;i++){
      if(!s.endless&&x>s.finish_distance+180)break;
      const o:Obstacle={id:w.serial++,x,width:40,kind:'spike',center:250,gap:s.gap_height,passed:false,pattern,section:this.section};
      if(s.mode==='ground'){
        const families=s.obstacles.filter(k=>!s.exclusions?.includes(k));
        o.kind=families[(pattern==='mixed'?i+Math.floor(r()*families.length):Math.floor(r()*families.length))%families.length];
        o.height=o.kind==='barrier'?45+Math.floor(r()*16):28+Math.floor(r()*13);
        const envelope=jumpEnvelope(s,o.kind==='gap'?0:o.height);
        const intensity=c.precision*(.65+.35*progress)*(pattern==='recovery'?.6:1);
        const scale=pattern==='escalation'?.55+.45*i/Math.max(1,count-1):.75+r()*.25;
        o.width=Math.max(18,Math.min(envelope.clearWidth*intensity*scale,o.kind==='gap'?240:130));
        // Independent grounded jumps. Separation uses MAX speed (shortest recovery)
        // while widths use MIN speed (shortest jump travel).
        const recovery=c.recovery+(1-progress)*.35+(pattern==='recovery'?.85:0)+(pattern==='rhythm'?i%2*.14:r()*.22);
        x+=o.width+s.max_speed*(envelope.flight+recovery);
      }else{
        o.kind='gate';o.width=36+Math.floor(r()*25);
        o.gap=Math.min(260,s.gap_height+(1-progress)*30+(pattern==='recovery'?25:0));
        const change=c.transition*progress;
        const base=w.lastCenter;
        o.center=pattern==='alternating'?270+(i%2===0?-1:1)*change/2:pattern==='ascending'?base-change*.5:pattern==='descending'?base+change*.5:pattern==='corridor'?base+(r()-.5)*change*.2:base+(r()-.5)*change;
        o.center=Math.max(o.gap/2+32,Math.min(508-o.gap/2,o.center));
        let lo:FlightState[]=[],hi:FlightState[]=[];
        // Repair by adding transit time and reducing transition, never shrinking
        // the collision box or claiming a failed search was playable.
        for(let attempt=0;attempt<7;attempt++){
          const travel=o.x+o.width+14-this.lastEnd;
          lo=reachableGate(s,this.low,travel,o,s.speed);
          hi=reachableGate(s,this.high,travel,o,s.max_speed);
          if(lo.length&&hi.length)break;
          this.repairs++;o.x+=s.max_speed*.18;o.center=(o.center+base)/2;
        }
        if(!lo.length||!hi.length)throw new Error('No reachable flying challenge under configured physics');
        this.low=lo;this.high=hi;this.lastEnd=o.x+o.width+14;w.lastCenter=o.center;
        x=o.x+o.width+s.max_speed*(c.spacing+(1-progress)*.4+(pattern==='recovery'?.7:0)+r()*.18);
      }
      this.pending.push(o);
    }
    this.section++;
  }
}
