import {useEffect,useRef,useState} from 'react';
import type {AdventureIR,AdventureUI} from '../game/adventure/types';

export function AdventureCanvas({spec,restart=0}:{spec:AdventureIR;restart?:number}) {
  const container=useRef<HTMLDivElement>(null);
  const control=useRef<(key:string,pressed:boolean)=>void>(()=>{});
  const [error,setError]=useState('');
  const [status,setStatus]=useState<AdventureUI|null>(null);
  useEffect(()=>{
    let disposed=false;let destroy:(()=>void)|undefined;
    Promise.all([import('phaser'),import('../game/adventure/AdventureScene')]).then(([{default:Phaser},{AdventureScene}])=>{
      if(disposed||!container.current)return;
      const game=new Phaser.Game({type:Phaser.AUTO,parent:container.current,width:960,height:540,pixelArt:true,
        scale:{mode:Phaser.Scale.FIT,autoCenter:Phaser.Scale.CENTER_BOTH},
        physics:{default:'arcade',arcade:{gravity:{x:0,y:0},debug:false}}});
      game.events.on('adventure-ui',(next:AdventureUI)=>setStatus(next));
      game.scene.add('Adventure',AdventureScene,true,{spec});
      control.current=(key,pressed)=>{game.scene.getScene('Adventure')?.events.emit('touch-control',key,pressed);};
      const prevent=(event:KeyboardEvent)=>{if(container.current?.contains(document.activeElement)&&['Space','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.code))event.preventDefault();};
      window.addEventListener('keydown',prevent);
      destroy=()=>{control.current=()=>{};window.removeEventListener('keydown',prevent);game.destroy(true);};
    }).catch(e=>setError(String(e)));
    return()=>{disposed=true;destroy?.();};
  },[spec,restart]);
  return <>
    <div className="game-surface" ref={container} tabIndex={0} onPointerDown={e=>e.currentTarget.focus()} aria-label="Adventure game. WASD or arrows move, E interact, F attack when equipped, R restart">{error&&<p role="alert">Game failed to load: {error}</p>}</div>
    {status&&<div className="adventure-mobile-status" aria-live="polite">
      <strong>{status.objective}</strong><span>{status.health}/{spec.gameplay?.health??5} hearts · {spec.gameplay&&spec.gameplay.outcome!=='quests'?`${(status.score||0).toFixed(1)}s`:`Quests ${status.progress} · Inventory: ${status.inventory}`}</span>
      {status.dialogue&&<p>{status.dialogue}<br/><small>Talk / Use · continue</small></p>}
    </div>}
    <div className="touch-controls">{[['left','←'],['up','↑'],['down','↓'],['right','→'],...(!spec.gameplay||spec.gameplay.outcome==='quests'?[['interact','Talk / Use']]:[]),...((spec.gameplay?spec.gameplay.player_attack:spec.combat)?[['attack','Attack']]:[])].map(([key,label])=><button key={key} aria-label={`Game ${key}`} onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);container.current?.focus();control.current(key,true);}} onPointerUp={()=>control.current(key,false)} onPointerCancel={()=>control.current(key,false)}>{label}</button>)}</div>
  </>;
}
