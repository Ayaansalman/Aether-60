import type { Actor, AdventureIR } from './types';

/** Persistent adventure state, independent of Phaser scenes and presentation. */
export class AdventureState {
  inventory: Record<string, number> = {};
  collected: Record<string, number> = {};
  removed = new Set<string>();
  activated = new Set<string>();
  unlocked = new Set<string>();
  defeated = new Set<string>();
  talked = new Set<string>();
  explored = new Set<string>();
  completed: boolean[];
  area = 0;
  health = 5;
  won = false;
  lost = false;
  spec: AdventureIR;
  constructor(spec: AdventureIR) { this.spec=spec; this.completed = spec.quests.map(() => false); }
  get current() { return this.completed.findIndex(v => !v); }
  get objective() {
    const q=this.spec.quests[this.current];
    if(!q)return 'All quests complete — use the glowing exit.';
    return q.kind==='collect'?`${q.text} (${Math.min(this.collected[q.target]||0,q.count)}/${q.count})`:q.text;
  }
  get states() { const active=this.current; return this.completed.map((v,i)=>v?'COMPLETED':i===active?'ACTIVE':'NOT_STARTED'); }
  settle() {
    // Retain real earlier events so exploratory pickups never disappear before a quest activates.
    for (let i=this.current; i>=0 && i<this.spec.quests.length; i++) {
      const q=this.spec.quests[i];
      const done=q.kind==='collect' ? (this.collected[q.target]||0)>=q.count :
        q.kind==='talk' ? this.talked.has(q.target) : q.kind==='explore' ? this.explored.has(q.target) :
        q.kind==='defeat' ? this.defeated.has(q.target) : q.kind==='activate' ? this.activated.has(q.target) :
        q.kind==='unlock' ? this.unlocked.has(q.target) : false;
      if (!done) break;
      this.completed[i]=true;
    }
  }
  pickup(actor: Actor, instance: string) {
    if (this.removed.has(instance)) return;
    this.removed.add(instance);
    if(actor.item)this.inventory[actor.item]=(this.inventory[actor.item]||0)+1;
    this.collected[actor.id]=(this.collected[actor.id]||0)+1;
    this.settle();
  }
  defeat(id: string) { this.defeated.add(id); this.settle(); }
  explore(id: string) { this.explored.add(id); this.settle(); }
  interact(actor: Actor): string[] {
    if (actor.kind==='npc') {
      const already=this.completed.some((done,i)=>done && this.spec.quests[i].target===actor.id && this.spec.quests[i].kind==='deliver');
      const first=!this.talked.has(actor.id);
      this.talked.add(actor.id); this.settle();
      const q=this.spec.quests[this.current];
      if (q?.kind==='deliver' && q.target===actor.id) {
        const needed=Object.keys(q.delivery_items||{}).length?q.delivery_items!:{[q.item]:q.count};
        if (Object.entries(needed).some(([item,count])=>(this.inventory[item]||0)<count)) return [...actor.dialogue.active,`Bring: ${Object.entries(needed).map(([item,n])=>`${n} ${item}`).join(', ')}.`];
        for(const [item,count] of Object.entries(needed))this.inventory[item]-=count;
        this.completed[this.current]=true; this.settle();
        return actor.dialogue.completed;
      }
      return already || this.current<0 ? actor.dialogue.completed : first ? actor.dialogue.greeting : actor.dialogue.active;
    }
    if (actor.kind==='switch') { this.activated.add(actor.id); this.settle(); return [`${actor.name} activated.`]; }
    if (actor.kind==='door') {
      const missing=actor.requires.filter(id=>!(this.inventory[id]>0) && !this.activated.has(id));
      if (missing.length) return [`${actor.name} is sealed. Requires: ${missing.join(', ')}.`];
      this.unlocked.add(actor.id); this.settle(); return [`${actor.name} unlocked. The passage is open.`];
    }
    if (actor.kind==='treasure') { this.pickup(actor,actor.id); return [`You found ${actor.name}!`]; }
    if (actor.kind==='landmark') { this.explore(actor.id); return [`Discovered: ${actor.name}.`]; }
    return [];
  }
  canLeave() {
    return this.spec.quests.every((q,i)=>this.completed[i] || this.spec.areas[this.area].actors.every(a=>a.id!==q.target));
  }
  leave() {
    if (!this.canLeave()) return false;
    if (this.area<this.spec.areas.length-1) this.area++;
    else this.won=this.current<0;
    return true;
  }
}
