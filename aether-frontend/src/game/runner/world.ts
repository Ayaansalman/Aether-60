import {ChallengeStream} from './challenges.ts';
export type RunnerIR={schema_version:'2.2';genre:'runner';title:string;seed:number;mode:'ground'|'flap';theme:'neon'|'forest'|'factory'|'sky'|'ice';player:'robot'|'creature'|'bird'|'cube';difficulty?:'easy'|'medium'|'hard'|'extreme';progression?:'stable'|'gradual'|'surge';visual_style?:'pixel';exclusions?:string[];challenge?:ChallengeDesign;endless:boolean;finish_distance:number;speed:number;max_speed:number;acceleration:number;gravity:number;jump_impulse:number;flap_impulse:number;gap_height:number;obstacles:('spike'|'gap'|'laser'|'barrier')[];scoring:'distance'|'gaps';unsupported:string[];requirements:{source:string;status:string}[]};
export type ChallengeDesign={patterns:string[];recovery:number;spacing:number;precision:number;transition:number;sequence_length:number;rest_every:number};
export type Obstacle={id:number;x:number;width:number;kind:string;center:number;gap:number;passed:boolean;pattern?:string;height?:number;section?:number};
/** Fixed-step simulation shared by browser and deterministic tests. All dimensions in pixels. */
export class RunnerWorld {
  spec:RunnerIR; y=250;vy=0;distance=0;score=0;elapsed=0;speed=0;state:'playing'|'lost'|'won'='playing';obstacles:Obstacle[]=[];nextX=850;serial=0;randomState=1;lastCenter=250;generation=0;accumulator=0;
  stream!:ChallengeStream;best=0;feedback=0;jumpBuffer=0;
  constructor(spec:RunnerIR){this.spec=spec;this.restart();}
  restart(){this.best=Math.max(this.best,this.score);this.feedback=0;this.jumpBuffer=0;this.y=this.spec.mode==='ground'?430:250;this.vy=0;this.distance=0;this.score=0;this.elapsed=0;this.speed=this.spec.speed;this.state='playing';this.obstacles=[];this.nextX=850;this.serial=0;this.randomState=this.spec.seed>>>0;this.lastCenter=250;this.accumulator=0;this.generation++;this.stream=new ChallengeStream(this);this.populate();}
  random(){this.randomState=(Math.imul(this.randomState,1664525)+1013904223)>>>0;return this.randomState/4294967296;}
  action(){if(this.state!=='playing'){this.restart();return;}if(this.spec.mode==='flap'){this.vy=-this.spec.flap_impulse;this.feedback=.18;}else {this.jumpBuffer=.10;if(this.y>=429.9&&this.vy===0){this.vy=-this.spec.jump_impulse;this.jumpBuffer=0;this.feedback=.18;}}}
  populate(){if(this.spec.challenge){this.stream.populate();return;}while(this.nextX<this.distance+1250){const flap=this.spec.mode==='flap';const kind=flap?'gate':this.spec.obstacles[Math.floor(this.random()*this.spec.obstacles.length)];
    this.lastCenter=Math.max(180,Math.min(330,this.lastCenter+(this.random()-.5)*100));
    const width=flap?64:kind==='gap'?this.speed*.23:kind==='barrier'?42:kind==='laser'?28:36;
    this.obstacles.push({id:this.serial++,x:this.nextX,width,kind,center:this.lastCenter,gap:this.spec.gap_height,passed:false});
    // Full jump flight plus reaction/landing margin, evaluated at maximum course speed.
    const interval=flap?1.65:2*this.spec.jump_impulse/this.spec.gravity+.72;
    this.nextX+=width+this.spec.max_speed*(interval+this.random()*.35);
  }}
  tick(seconds:number){this.accumulator+=Math.min(.1,Math.max(0,seconds));while(this.accumulator>=1/120){this.step(1/120);this.accumulator-=1/120;}}
  step(dt:number){if(this.state!=='playing')return;this.elapsed+=dt;this.feedback=Math.max(0,this.feedback-dt);this.jumpBuffer=Math.max(0,this.jumpBuffer-dt);const ramp=this.spec.progression==='stable'?0:this.spec.progression==='surge'?Math.floor(this.elapsed/12)*12:this.elapsed;this.speed=Math.min(this.spec.max_speed,this.spec.speed+ramp*this.spec.acceleration);this.distance+=this.speed*dt;this.vy+=this.spec.gravity*dt;this.y+=this.vy*dt;
    const px=this.distance+180,r=14;
    const overGap=this.obstacles.some(o=>o.kind==='gap'&&px>o.x&&px<o.x+o.width);
    if(this.spec.mode==='ground'&&!overGap&&this.y>=430&&this.vy>=0&&this.y-this.vy*dt<=438){this.y=430;this.vy=0;if(this.jumpBuffer>0){this.vy=-this.spec.jump_impulse;this.jumpBuffer=0;this.feedback=.18;}}
    for(const o of this.obstacles){if(!o.passed&&px-r>o.x+o.width){o.passed=true;if(this.spec.scoring==='gaps')this.score++;}
      if(px+r>o.x&&px-r<o.x+o.width){if(o.kind==='gate'?(this.y-r<o.center-o.gap/2||this.y+r>o.center+o.gap/2):o.kind==='gap'?this.y>446:this.y+r>444-(o.height??(o.kind==='barrier'?60:40)))this.state='lost';}}
    if(this.y<14||this.y>526)this.state='lost';
    if(this.spec.scoring==='distance')this.score=Math.floor(this.distance/10);
    this.best=Math.max(this.best,this.score);
    if(!this.spec.endless&&this.distance>=this.spec.finish_distance&&this.state==='playing')this.state='won';
    this.obstacles=this.obstacles.filter(o=>o.x+o.width>this.distance-100);this.populate();
  }
}
