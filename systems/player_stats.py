
from systems.character_progression import CharacterProgression,calculate,ensure,read,PLAYER
def get_player_stats():
    p=ensure(read(PLAYER,{}))
    final=calculate(p)
    return {'base':p['base_stats'],'bonuses':{},'final':final,'equipment':read_equipment()}
def read_equipment():
    from systems.character_progression import read,INV
    return read(INV,{}).get('equipment',{})
