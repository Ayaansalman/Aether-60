"""Deterministic acceptance specifications; no provider calls or database writes."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from services import runner
from services.semantic_intent import interpret,fidelity
PROMPTS={
'A':'Create an easy endless runner through an enchanted forest. The player is a small woodland creature that automatically runs forward. Include gentle jumps, widely spaced obstacles, charming forest scenery, and gradual difficulty progression.',
'B':'Create an extremely difficult endless runner through a dangerous futuristic factory. The player automatically sprints forward and must perform precision jumps across gaps, spikes, and rapid obstacle sequences. Make the game fast, intense, and increasingly challenging.',
'C':'Create a friendly colorful flying game for beginners. I control a little bird by tapping to stay airborne. Include large obstacle gaps, slow scrolling, gentle height changes, and forgiving difficulty.',
'D':'Create a very difficult endless flying game through an icy cavern. I must precisely flap between narrow gaps, navigate alternating high and low passages, and survive increasingly fast obstacle sequences.',
}
def prepare():
    out=ROOT/'docs/evidence/iteration8';out.mkdir(parents=True,exist_ok=True)
    for key,prompt in PROMPTS.items():
        intent,_=interpret(prompt,'fixture');d,_=runner.plan(prompt,'fixture',intent.model_dump());ir=runner.construct(d,prompt,7)
        directory=out/key;directory.mkdir(exist_ok=True)
        for name,data in [('spec',ir.model_dump()),('intent',intent.model_dump()),('semantic_requirement_report',fidelity(ir,intent.model_dump()))]:
            (directory/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        (directory/'prompt.txt').write_text(prompt,encoding='utf-8')
        print(key,ir.mode,ir.difficulty,ir.theme,ir.speed,ir.max_speed,ir.gap_height)
if __name__=='__main__':prepare()
