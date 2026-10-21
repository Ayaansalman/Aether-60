import {useEffect,useRef} from 'react';
import {ArcadePainter} from '../game/runner/presentation';
import {RunnerWorld} from '../game/runner/world';
import type {RunnerIR} from '../game/runner/world';
declare global {interface Window {__runner?:{world:RunnerWorld;action:()=>void;restart:()=>void;snapshot:()=>unknown}}}
export function RunnerCanvas({spec,restart=0}:{spec:RunnerIR;restart?:number}){
 const canvas=useRef<HTMLCanvasElement>(null);const bests=useRef(new Map<string,number>());
 useEffect(()=>{const el=canvas.current!;const ctx=el.getContext('2d')!;const world=new RunnerWorld(spec);const bestKey=JSON.stringify(spec);world.best=bests.current.get(bestKey)??0;const sessionBests=bests.current;const painter=new ArcadePainter(spec.theme,spec.player);let frame=0,last=0,lostAt=0;
 const action=()=>world.action();const key=(e:KeyboardEvent)=>{if(document.activeElement!==el)return;if(['Space','ArrowUp','KeyW','KeyR','Enter'].includes(e.code)){e.preventDefault();if(!e.repeat){if(e.code==='KeyR')world.restart();else action();}}};
 const pointer=()=>{el.focus();action();};el.addEventListener('pointerdown',pointer);window.addEventListener('keydown',key);
 const hook={world,action,restart:()=>world.restart(),snapshot:()=>({mode:spec.mode,state:world.state,score:world.score,distance:world.distance,y:world.y,vy:world.vy,active:world.obstacles.length,serial:world.serial,generation:world.generation})};window.__runner=hook;
 const draw=(now:number)=>{const dt=last?(now-last)/1000:0;last=now;if(document.activeElement===el)world.tick(dt);
 if(world.state==='playing')lostAt=0;else if(!lostAt)lostAt=now;
 ctx.save();if(world.state==='lost'&&now-lostAt<180)ctx.translate(Math.sin(now*.12)*3,Math.cos(now*.1)*2);painter.draw(ctx,world,now);ctx.restore();
 if(world.state==='lost'&&now-lostAt<250){ctx.strokeStyle=`rgba(255,110,110,${1-(now-lostAt)/250})`;ctx.lineWidth=8;ctx.strokeRect(4,4,952,532);}
 const compact=el.clientWidth<600;ctx.fillStyle='#102135df';ctx.fillRect(12,12,936,compact?88:64);ctx.fillStyle='#fff';ctx.font=`bold ${compact?34:20}px monospace`;ctx.fillText(spec.title.slice(0,compact?24:50),26,compact?43:38);ctx.textAlign='right';ctx.fillText(`${world.score}${spec.scoring==='distance'?'m':''} · Best ${world.best}`,930,compact?43:38);ctx.textAlign='left';ctx.font=`${compact?28:14}px monospace`;
 const pattern=world.obstacles.find(o=>o.x+o.width>world.distance+180)?.pattern??'intro';
 ctx.fillStyle='#bee7e3';ctx.fillText(`${spec.difficulty??'medium'} · ${Math.round(world.speed)} px/s · ${pattern} · ${compact?'Tap': 'Space / tap'} ${spec.mode==='flap'?'flap':'jump'}${compact?'':' · R restart'}`,26,compact?78:64);
 if(world.state!=='playing'||document.activeElement!==el){ctx.fillStyle='#102135ed';ctx.fillRect(220,220,520,94);ctx.fillStyle='#fff';ctx.font='bold 23px monospace';ctx.textAlign='center';ctx.fillText(world.state==='lost'?'CRASHED · Tap / Space to retry':world.state==='won'?'FINISH! · Tap / Space to retry':'Tap to start',480,258);ctx.font='16px monospace';ctx.fillStyle='#bee7e3';ctx.fillText(world.state==='playing'?(spec.mode==='flap'?'Tap repeatedly to fly between passages':'Automatic running · time your jumps'):`Score ${world.score} · Session best ${world.best}`,480,290);ctx.textAlign='left';}
 frame=requestAnimationFrame(draw);};frame=requestAnimationFrame(draw);
 return()=>{sessionBests.set(bestKey,world.best);cancelAnimationFrame(frame);window.removeEventListener('keydown',key);el.removeEventListener('pointerdown',pointer);if(window.__runner===hook)delete window.__runner;};},[spec,restart]);
 return <canvas className="game-surface" ref={canvas} width={960} height={540} tabIndex={0} style={{width:'100%',touchAction:'none'}} aria-label={`${spec.mode} runner. Space or tap to ${spec.mode==='flap'?'flap':'jump'}. R to restart.`}/>;
}
