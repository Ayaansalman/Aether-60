import {Check,Loader2,Gamepad2,X,ArrowRight} from 'lucide-react';
import type {generationView} from '../game/generation';

export function GenerationProgress({view}:{view:ReturnType<typeof generationView>}){
  return <div className={`generation-canvas ${view.phase}`} data-testid="generation-progress" aria-busy={view.phase==='building'}>
    <div className="generation-canvas-heading" role="status" aria-live="polite">
      {view.phase==='building'?<Loader2 className="spin" size={27}/>:view.phase==='failed'?<X size={27}/>:<Gamepad2 size={27}/>}
      <div><h3>{view.title}</h3><p>{view.message}</p></div>
    </div>
    {!!view.progress.length&&<ol className="generation-timeline" aria-label="Backend generation steps">
      {view.progress.slice(-9).map(step=><li key={step.id} className={step.state} aria-current={step.state==='active'?'step':undefined}>
        <span className="generation-step-icon">{step.state==='active'?<Loader2 size={15} className="spin"/>:step.state==='failed'?<X size={15}/>:step.state==='info'?<ArrowRight size={15}/>:<Check size={15}/>}</span>
        <div><strong>{step.label}</strong><p>{step.detail}</p></div>
        <small>{step.state==='active'?'In progress':step.state==='failed'?'Stopped':step.state==='info'?'Fallback':'Finished'}</small>
      </li>)}
    </ol>}
  </div>;
}
