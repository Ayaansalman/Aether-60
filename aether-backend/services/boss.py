"""One-on-one arena composition with a single designated encounter target."""
import hashlib
from schemas.platformer import PlatformerIR,Platform,Entity,Player,Goal

def construct_arena(design,prompt,seed=None):
    boss=design.boss
    seed=seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8],16)
    return PlatformerIR(title=design.title,theme=design.theme,seed=seed,width=1008,height=648,
        spawn={'x':160,'y':475},player=Player(abilities=design.abilities,health=5),
        platforms=[Platform(x=i*8,y=14,width=8,kind='ruins') for i in range(4)],
        entities=[Entity(id='arena_boss',x=760,y=470,kind='enemy',platform=2,boss=boss)],
        boss=boss,player_attack='projectile',objective={'type':'boss_defeat','required':0,'total':0},
        goals=[Goal(id='defeat_boss',kind='defeat',targets=['arena_boss'],count=1)],
        briefing='One-on-one duel. F / X fires your combat ability. Red flash warns of a charge or volley.',
        requirements=[{'id':'boss_duel','source':'Boss duel','status':'constructed_unverified'}])
