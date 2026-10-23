import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generationView} from '../src/game/generation.ts';

const job=(status,artifacts={})=>({job:{game_id:'case',status,prompt:'A runner',limitations:[],model_id:'primary'},events:[{id:1,stage:'PLANNING',detail:'Interpreting central loop, controls and constraints',result:'START'},{id:2,stage:'TESTING',detail:'Running real Chromium checks',result:'START'}],artifacts});

test('a constructed specification cannot unlock play before QA passes',()=>{
 for(const status of ['PLANNING','DESIGNING','BUILDING','TESTING','REPAIRING']){
  assert.equal(generationView(job(status,{'game_ir_v2.json':{genre:'runner'},'qa_report.json':{overall:'PASS'}}),false,'').ready,false);
 }
 assert.equal(generationView(job('READY',{'qa_report.json':{overall:'PASS'}}),false,'').ready,true);
 assert.equal(generationView(job('READY_WITH_WARNINGS',{'qa_report.json':{overall:'PASS'},'semantic_requirement_report.json':{overall:'WARN'}}),false,'').ready,true);
});

test('missing or unavailable QA stays blocked even with a terminal warning status',()=>{
 for(const overall of [undefined,'UNAVAILABLE','UNVERIFIED','FAIL']){
  const view=generationView(job('READY_WITH_WARNINGS',{'qa_report.json':{overall}}),false,'');
  assert.equal(view.ready,false);assert.ok(['failed','unverified'].includes(view.phase));
 }
 assert.equal(generationView(job('READY',{'qa_report.json':{overall:'PASS'}}),true,'').ready,false);
});

test('core semantic failure and exact failed QA invariants are preserved',()=>{
 const data=job('FAILED',{'qa_report.json':{overall:'FAIL',checks:[{id:'shared_gate_dependency',passed:false}]},'semantic_requirement_report.json':{overall:'FAIL',requirements:[{source:'Both switches open the final gate',status:'failed'}]}});
 data.events.push({id:3,stage:'FAILED',detail:'Gate dependency was not preserved',result:'FAILED'});
 const view=generationView(data,false,'');assert.equal(view.phase,'failed');
 assert.ok(view.failures.some(f=>f.includes('Gate dependency')));assert.ok(view.failures.some(f=>f.includes('Both switches')));assert.ok(view.failures.some(f=>f.includes('shared gate dependency')));
});

test('real fallback events do not falsely finish the active planning step',()=>{
 const data=job('PLANNING');data.events=data.events.slice(0,1);data.events.push({id:2,stage:'MODEL_FALLBACK',detail:'primary → backup: quota limit',result:'START'});
 const view=generationView(data,false,'');assert.equal(view.progress[0].label,'Understanding your request');assert.equal(view.progress[0].state,'active');assert.equal(view.progress[1].state,'info');assert.equal(view.ready,false);
});

test('connection failure hides stale playable output and can recover without a new job',()=>{
 const data=job('READY',{'qa_report.json':{overall:'PASS'}});
 assert.equal(generationView(data,false,'Network disconnected').phase,'connection');
 assert.equal(generationView(data,false,'Network disconnected').ready,false);
 assert.equal(generationView(data,false,'').ready,true);
 assert.equal(generationView(null,false,'Network disconnected',true).title,'Connection interrupted');
});

test('a passing recheck replaces stale original failure, but the newest failing recheck blocks play',()=>{
 const data=job('READY_WITH_WARNINGS',{'qa_report.json':{overall:'FAIL'},'qa_retest_1.json':{overall:'PASS'}});
 data.events.push({id:3,stage:'FAILED',detail:'Historical failure',result:'FAILED'});
 assert.equal(generationView(data,false,'').ready,true);
 data.artifacts['qa_retest_2.json']={overall:'FAIL'};
 assert.equal(generationView(data,false,'').ready,false);
 data.artifacts['qa_retest_10.json']={overall:'PASS'};
 assert.equal(generationView(data,false,'').ready,true);
 data.artifacts['semantic_requirement_report.json']={overall:'FAIL'};
 assert.equal(generationView(data,false,'').ready,false);
 data.job.status='TESTING';
 const running=generationView(data,true,'');
 assert.equal(running.ready,false);assert.equal(running.phase,'building');
 assert.equal(running.progress.at(-1).state,'active');
});
