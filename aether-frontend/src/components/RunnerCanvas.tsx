import {useEffect,useRef} from 'react';
import {RunnerWorld} from '../game/runner/world';
import type {RunnerIR} from '../game/runner/world';
declare global {interface Window {__runner?:{world:RunnerWorld;action:()=>void;restart:()=>void;snapshot:()=>unknown}}}
export function RunnerCanvas({spec,restart=0}:{spec:RunnerIR;restart?:number}){
 const canvas=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{const el=canvas.current!;const ctx=el.getContext('2d')!;const world=new RunnerWorld(spec);let frame=0,last=0;
 const action=()=>world.action();const key=(e:KeyboardEvent)=>{if(document.activeElement!==el)return;if(['Space','ArrowUp','KeyW','KeyR','Enter'].includes(e.code)){e.preventDefault();if(!e.repeat){if(e.code==='KeyR')world.restart();else action();}}};
 const pointer=()=>{el.focus();action();};el.addEventListener('pointerdown',pointer);window.addEventListener('keydown',key);
 const hook={world,action,restart:()=>world.restart(),snapshot:()=>({mode:spec.mode,state:world.state,score:world.score,distance:world.distance,y:world.y,vy:world.vy,active:world.obstacles.length,serial:world.serial,generation:world.generation})};window.__runner=hook;
 const draw=(now:number)=>{const dt=last?(now-last)/1000:0;last=now;if(document.activeElement===el)world.tick(dt);
 const neon=spec.theme==='neon';ctx.fillStyle=neon?'#10112d':spec.theme==='ice'?'#a6cfe5':spec.theme==='forest'?'#254b50':'#8ed9ef';ctx.fillRect(0,0,960,540);
 for(let i=0;i<14;i++){
 const x=((i*100-world.distance*.22)%1400+1400)%1400-100;
 if(spec.theme==='sky'){if(i%2===0){ctx.fillStyle='#ffffff99';ctx.beginPath();ctx.ellipse(x,145+(i%4)*45,75,22,0,0,Math.PI*2);ctx.fill();}}
 else if(spec.theme==='forest'){ctx.fillStyle='#42695e';ctx.fillRect(x+26,250,18,240);ctx.fillStyle='#438675';ctx.beginPath();ctx.ellipse(x+35,245,75,100,0,0,Math.PI*2);ctx.fill();}
 else if(spec.theme==='ice'){ctx.fillStyle='#e5f3fa';ctx.beginPath();ctx.moveTo(x-40,500);ctx.lineTo(x+40,190+i%3*40);ctx.lineTo(x+160,500);ctx.fill();}
 else{ctx.fillStyle='#292554';ctx.fillRect(x,180+(i%4)*35,70,310);ctx.fillStyle='#39ded2';ctx.fillRect(x+12,210+(i%4)*35,5,80);}
}
 if(spec.mode==='ground'){ctx.fillStyle=neon?'#38e8ce':'#6bac69';ctx.fillRect(0,444,960,96);}
 for(const o of world.obstacles){const x=o.x-world.distance;ctx.fillStyle=o.kind==='gap'?'#10112d':neon?'#ff498d':'#a758b6';if(o.kind==='gate'){ctx.fillRect(x,0,o.width,o.center-o.gap/2);ctx.fillRect(x,o.center+o.gap/2,o.width,540);ctx.fillStyle='#fff0b0';ctx.fillRect(x-4,o.center-o.gap/2-10,o.width+8,10);ctx.fillRect(x-4,o.center+o.gap/2,o.width+8,10);}else if(o.kind==='gap')ctx.fillRect(x,444,o.width,96);else if(o.kind==='spike'){ctx.beginPath();ctx.moveTo(x,444);ctx.lineTo(x+o.width/2,404);ctx.lineTo(x+o.width,444);ctx.fill();}else{ctx.fillRect(x,444-(o.kind==='barrier'?60:40),o.width,o.kind==='barrier'?60:40);if(o.kind==='laser'){ctx.fillStyle='#fff';ctx.fillRect(x+8,404,4,40);}}}
 ctx.save();ctx.translate(180,world.y);ctx.fillStyle='#ffe597';if(spec.player==='creature'){ctx.beginPath();ctx.ellipse(0,0,17,13,0,0,7);ctx.fill();ctx.fillStyle='#f38b85';ctx.beginPath();ctx.ellipse(-5,Math.sin(now/90)*8,13,6,-.4,0,7);ctx.fill();}else{ctx.fillRect(-14,-14,28,28);ctx.fillStyle='#72e5ed';ctx.fillRect(-9,-9,18,10);}ctx.fillStyle='#1b2340';ctx.fillRect(6,-7,4,4);ctx.restore();
 const compact=el.clientWidth<600;ctx.fillStyle='#10112ddf';ctx.fillRect(12,12,compact?930:910,compact?110:78);ctx.fillStyle='#fff';ctx.font=`bold ${compact?36:22}px monospace`;ctx.fillText(spec.title.slice(0,compact?24:60),26,compact?48:40);ctx.font=`${compact?32:16}px monospace`;ctx.fillText(`${spec.mode==='flap'?'Gaps':'Distance'}: ${world.score}${spec.scoring==='distance'?'m':''} · ${compact?'Tap':'Space / tap'}: ${spec.mode==='flap'?'flap':'jump'}${compact?'':' · R: restart'}`,26,compact?96:70);
 if(world.state!=='playing'||document.activeElement!==el){ctx.fillStyle='#10112de8';ctx.fillRect(180,205,600,116);ctx.fillStyle='#fff';ctx.font='bold 25px monospace';ctx.fillText(world.state==='lost'?'CRASHED — Space / tap to restart':world.state==='won'?'FINISH! — Space / tap to restart':'Click or tap to play',205,251);ctx.font='17px monospace';ctx.fillText('Space / tap '+(spec.mode==='flap'?'applies upward impulse':'jumps; forward motion is automatic'),205,288);}
 frame=requestAnimationFrame(draw);};frame=requestAnimationFrame(draw);
 return()=>{cancelAnimationFrame(frame);window.removeEventListener('keydown',key);el.removeEventListener('pointerdown',pointer);if(window.__runner===hook)delete window.__runner;};},[spec,restart]);
 return <canvas className="game-surface" ref={canvas} width={960} height={540} tabIndex={0} style={{width:'100%',touchAction:'none'}} aria-label={`${spec.mode} runner. Space or tap to ${spec.mode==='flap'?'flap':'jump'}. R to restart.`}/>;
}
