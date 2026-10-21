import {useEffect,useRef,useState} from 'react';
import type {SurvivalIR} from '../game/survival/stream';
export function SurvivalCanvas({spec,restart=0}:{spec:SurvivalIR;restart?:number}){
 const root=useRef<HTMLDivElement>(null);const controls=useRef<(key:string,pressed:boolean)=>void>(()=>{});const[error,setError]=useState('');const[status,setStatus]=useState<{health:number;max:number;seconds:number}|null>(null);
 useEffect(()=>{let disposed=false;let destroy:(()=>void)|undefined;
 Promise.all([import('phaser'),import('../game/ArenaScene')]).then(([{default:Phaser},{ArenaScene}])=>{
  if(disposed||!root.current)return;
  const game=new Phaser.Game({type:Phaser.AUTO,parent:root.current,width:960,height:540,scale:{mode:Phaser.Scale.FIT,autoCenter:Phaser.Scale.CENTER_BOTH},physics:{default:'arcade',arcade:{gravity:{x:0,y:0}}}});
  game.events.on('survival-ui',setStatus);
  game.scene.add('ArenaScene',ArenaScene,true,{gameIR:spec});controls.current=(key,pressed)=>game.scene.getScene('ArenaScene')?.events.emit('survival-control',key,pressed);
  const prevent=(e:KeyboardEvent)=>{if(root.current?.contains(document.activeElement)&&e.code.startsWith('Arrow'))e.preventDefault();};window.addEventListener('keydown',prevent);
  destroy=()=>{controls.current=()=>{};window.removeEventListener('keydown',prevent);game.destroy(true);};
 }).catch(e=>setError(String(e)));
 return()=>{disposed=true;destroy?.();};},[spec,restart]);
 return <><div className="game-surface" ref={root} tabIndex={0} onPointerDown={e=>e.currentTarget.focus()} aria-label="Top-down survival. Click to focus, WASD or arrows move, R restarts.">{error&&<p role="alert">{error}</p>}</div>{status&&<div className="adventure-mobile-status" aria-live="polite"><strong>{status.health}/{status.max} health · Survived {status.seconds}s</strong><span>Red C: chaser · Amber S: fires {spec.survival_stream.shooter_shots} shots, {spec.survival_stream.shot_interval_ms/1000}s apart, then expires.</span></div>}<div className="touch-controls">{[['left','←'],['up','↑'],['down','↓'],['right','→'],['restart','Restart']].map(([key,label])=><button key={key} aria-label={`Game ${key}`} onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);root.current?.focus();controls.current(key,true);}} onPointerUp={()=>controls.current(key,false)} onPointerCancel={()=>controls.current(key,false)}>{label}</button>)}</div></>;
}
