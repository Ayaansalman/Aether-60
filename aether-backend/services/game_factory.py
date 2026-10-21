"""Genre dispatch boundary for v2; platformer contracts remain unchanged."""
from services.adventure import is_adventure


def genre_for_prompt(prompt: str) -> str:
    return 'adventure' if is_adventure(prompt) else 'platformer'


def parse_ir(data):
    from schemas.adventure import AdventureIR
    from schemas.platformer import PlatformerIR
    return (AdventureIR if data.get('genre')=='adventure' else PlatformerIR).model_validate(data)
