"""Retest a saved live design after explicit registered-capability normalization; zero model calls."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from schemas.adventure import AdventureDesign
from services import adventure
from services.adventure_qa import run_browser_qa
from services.semantic_intent import fidelity
source=ROOT/'docs/evidence/iteration7/api-live-B/result.json';result=json.loads(source.read_text(encoding='utf-8'));original=result['artifacts'];design=AdventureDesign.model_validate(original['model_design.json']);prompt=result['job']['prompt']
out=source.parent/'saved-design-retest';out.mkdir(exist_ok=True)
guard=adventure.enforce_requirements(design,prompt);ir=adventure.construct(design,prompt,7)
report=run_browser_qa('http://localhost:5173/studio?example=forest',out,ir.model_dump());semantic=fidelity(ir,original['semantic_intent.json'],report)
for name,value in [('guard',guard),('design',design.model_dump()),('spec',ir.model_dump()),('semantic_requirement_report',semantic),('provenance',{'source':str(source.relative_to(ROOT)),'model_calls':0,'original_model':original['provider.json']['model'],'method':'Saved real-model design; bounded registered capability normalization and current runtime retest'})]:
 (out/(name+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
print({'qa':report['overall'],'semantic':semantic['overall'],'unsupported':ir.unsupported,'normalizations':guard['changes']})
