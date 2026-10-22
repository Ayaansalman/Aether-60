"""One-on-one arena composition with a single designated encounter target."""
import hashlib
from schemas.platformer import PlatformerIR,Platform,Entity,Player,Goal

def construct_arena(design,prompt,seed=None):
    boss=design.boss
    seed=seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8],16)
    tiles=28+(seed%3)*2;width=tiles*36
    floor=[Platform(x=x,y=14,width=min(8,tiles-x),kind='ruins') for x in range(0,tiles,8)]
    boss_x=width-248;support=next(i for i,p in enumerate(floor) if p.x*36<=boss_x<(p.x+p.width)*36)
    return PlatformerIR(title=design.title,theme=design.theme,seed=seed,width=width,height=648,
        spawn={'x':160,'y':475},player=Player(abilities=design.abilities,health=5),
        platforms=floor,
        entities=[Entity(id='arena_boss',x=boss_x,y=470,kind='enemy',platform=support,boss=boss)],
        boss=boss,player_attack='projectile',objective={'type':'boss_defeat','required':0,'total':0},
        goals=[Goal(id='defeat_boss',kind='defeat',targets=['arena_boss'],count=1)],
        briefing='F / X attacks. Dodge charges and volleys'+('; jump over the ground slam.' if 'slam' in boss.patterns else '.'),
        requirements=[{'id':'boss_duel','source':'Boss duel','status':'constructed_unverified'}])
