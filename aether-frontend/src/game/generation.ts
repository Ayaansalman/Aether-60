import type {StudioJob} from './platformer/types.ts';

type Report={overall?:string;checks?:{id:string;passed:boolean;critical?:boolean;details?:unknown}[];requirements?:{source:string;status:string;mandatory?:boolean;category?:string}[]};
const terminal=new Set(['READY','READY_WITH_WARNINGS','FAILED']);
const labels:Record<string,string>={QUEUED:'Request queued',PLANNING:'Planning the game',DESIGNING:'Constructing the world',SELECTING_ASSETS:'Selecting artwork',VALIDATING_SPEC:'Validating mechanics',BUILDING:'Preparing the runtime',TESTING:'Running gameplay QA',REPAIRING:'Repairing and rechecking',MODEL_FALLBACK:'Switching API model',READY:'Ready to play',READY_WITH_WARNINGS:'Ready with limitations',FAILED:'Generation stopped'};
export function stageLabel(stage:string,detail=''){
  return stage==='PLANNING'&&/interpreting|intent parsing/i.test(detail)?'Understanding your request':labels[stage]??stage.replaceAll('_',' ').toLowerCase();
}

export function generationView(job:StudioJob|null,busy:boolean,error:string,hasSavedJob=!!job){
  // Explicit rechecks are immutable numbered reports. Older backends left the
  // original canonical filename unchanged, so use the newest completed recheck.
  const latest=Object.keys(job?.artifacts??{}).filter(name=>/^qa_retest_\d+\.json$/.test(name))
    .sort((a,b)=>Number(b.match(/\d+/)?.[0])-Number(a.match(/\d+/)?.[0]))[0];
  const qa=job?.artifacts[latest??'qa_report.json'] as Report|undefined;
  const semantic=job?.artifacts['semantic_requirement_report.json'] as Report|undefined;
  const requirements=job?.artifacts['requirement_report.json'] as Report|undefined;
  const status=job?.job.status;
  const finished=!!status&&terminal.has(status);
  const failed=status==='FAILED'||(finished&&(semantic?.overall==='FAIL'||requirements?.overall==='FAIL'||qa?.overall==='FAIL'));
  const ready=!!status&&['READY','READY_WITH_WARNINGS'].includes(status)&&qa?.overall==='PASS'&&!failed&&!error&&!busy;
  const phase=error&&!failed?'connection':busy?'building':failed?'failed':ready?'ready':finished?'unverified':job?'building':'idle';
  const failures:string[]=[];
  if(failed){
    const event=[...(job?.events??[])].reverse().find(e=>e.stage==='FAILED');
    if(event?.detail)failures.push(event.detail);
    for(const c of qa?.checks??[])if(!c.passed&&c.critical!==false)failures.push('Gameplay check failed: '+c.id.replaceAll('_',' '));
    for(const r of semantic?.requirements??[])if(r.status==='failed'||r.status==='unsupported'&&r.mandatory!==false&&r.category!=='presentation')failures.push('Required feature: '+r.source);
  }
  if(error&&!failures.includes(error))failures.push(error);
  const steps=(job?.events??[]).filter(e=>!['READY','READY_WITH_WARNINGS','FAILED'].includes(e.stage));
  const reverseLast=[...steps].reverse().findIndex(e=>e.stage!=='MODEL_FALLBACK');
  const last=reverseLast<0?-1:steps.length-1-reverseLast;
  const progress=steps.map((e,i)=>({...e,label:stageLabel(e.stage,e.detail),state:e.stage==='MODEL_FALLBACK'?'info':i===last?(failed||finished&&!ready?'failed':finished?'done':'active'):'done'}));
  return {phase,ready,finished,qa:qa?.overall,failures:[...new Set(failures)].slice(0,5),progress,
    title:phase==='failed'?'Your game needs attention':phase==='connection'?(hasSavedJob?'Connection interrupted':'Your request could not be started'):phase==='unverified'?'Gameplay verification is incomplete':phase==='idle'?'Your next world belongs here.':'Building your world',
    message:phase==='failed'?'The game is held back because required checks did not pass. See the details below.':phase==='connection'?(hasSavedJob?'Reconnect to check the saved job’s progress.':'Check the message below, then retry your request.'):phase==='unverified'?'The specification was saved, but QA has not passed. Run verification again before playing.':phase==='idle'?'Describe a platformer, adventure or arcade runner, then select Generate game.':'Follow the actual backend steps below. Your game will appear after gameplay QA passes.'};
}
