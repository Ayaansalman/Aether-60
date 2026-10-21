"""Genre dispatch boundary for v2; platformer contracts remain unchanged."""
from services.adventure import is_adventure


def genre_for_prompt(prompt: str) -> str:
    import re
    if re.search(r'surviv|evad|dodg',prompt,re.I) and re.search(r'bullets?|shooters?|enemy.*spawn',prompt,re.I) and not re.search(r'platformer|runner|flap',prompt,re.I):return 'arena_survival'
    if re.search(r'runner|auto[ -]?run|flap|tap.*(?:airborne|fly)|flying.*(?:tap|space)',prompt,re.I): return 'runner'
    return 'adventure' if is_adventure(prompt) else 'platformer'


def parse_ir(data):
    from schemas.adventure import AdventureIR
    from schemas.platformer import PlatformerIR
    from schemas.runner import RunnerIR
    from schemas.survival import SurvivalIR
    if data.get('genre')=='arena_survival':return SurvivalIR.model_validate(data)
    if data.get('genre')=='runner': return RunnerIR.model_validate(data)
    return (AdventureIR if data.get('genre')=='adventure' else PlatformerIR).model_validate(data)
