
import json, os, copy, math
from pathlib import Path
from systems.save_store import read_json as persistent_read, write_json as persistent_write
ROOT=Path(__file__).resolve().parents[1]
PLAYER=ROOT/'data/player/player_data.json'
INV=ROOT/'data/player/inventory.json'
DB=ROOT/'data/items/item_database.json'
STATS=('str','vit','int','spi','agi','luk')
INITIAL={
 'balanced_mage':(10,10,13,13,10,10),
 'melee_mage':(15,14,9,10,10,8),
 'ranged_mage':(7,8,16,15,12,8)}
CLASS_NAMES={'balanced_mage':'均衡型法師','melee_mage':'近戰型法師','ranged_mage':'遠程型法師'}
AFFINITIES=('fire','water','wind','lightning','light','dark')
def read(path, default):
    return persistent_read(path, default)
def write(path, data):
    persistent_write(path, data)
def defaults(class_id):
    return dict(zip(STATS,INITIAL.get(class_id,INITIAL['balanced_mage'])))
def ensure(data):
    data=copy.deepcopy(data)
    cid=data.get('class_id') or 'balanced_mage'
    data.setdefault('class_id',cid)
    data.setdefault('class_name',CLASS_NAMES.get(cid,'均衡型法師'))
    level=max(1,int(data.get('level',1)))
    data['level']=level
    data.setdefault('exp',0)
    data.setdefault('exp_to_next_level',100*level)
    data.setdefault('gold',0)
    # 不覆蓋舊角色資料；新版能力值只在第一次建立時初始化
    if not isinstance(data.get('base_stats'),dict):
        data['base_stats']=defaults(cid)
    for key,value in defaults(cid).items(): data['base_stats'].setdefault(key,value)
    data.setdefault('unspent_points',5*(level-1))
    data.setdefault('allocated_points',0)
    if not isinstance(data.get('hidden_talents'),dict):
        data['hidden_talents']={}
    h=data['hidden_talents']
    h.setdefault('element_affinity',{k:0 for k in AFFINITIES})
    h.setdefault('magic_control',0)
    h.setdefault('magic_affinity',0)
    h.setdefault('perception',0)
    h.setdefault('willpower',0)
    h.setdefault('special_talents',[])
    return data

def equipment_bonus():
    inv=read(INV,{})
    db=read(DB,{})
    if isinstance(db,dict) and isinstance(db.get('items'),list):
        db={x['id']:x for x in db['items'] if 'id' in x}
    out={}
    for item_id in inv.get('equipment',{}).values():
        item=db.get(item_id,{}) if item_id else {}
        for field in ('bonuses','advanced_bonuses'):
            for k,v in item.get(field,{}).items():
                if isinstance(v,(int,float)): out[k]=out.get(k,0)+v
    return out

def calculate(data):
    data=ensure(data)
    a=data['base_stats']; lv=data['level']; b=equipment_bonus()
    # 舊版裝備欄位 attack / defense / magic 保持有效
    result={
      'physical_attack':2*a['str']+0.3*a['agi']+b.get('physical_attack',0)+b.get('attack',0),
      'magic_attack':2*a['int']+0.5*a['spi']+b.get('magic_attack',0)+b.get('magic',0),
      'physical_defense':1.5*a['vit']+0.3*a['str']+b.get('physical_defense',0)+b.get('defense',0),
      'magic_defense':1.3*a['int']+0.7*a['spi']+b.get('magic_defense',0),
      'crit_rate':min(75,max(0,5+0.12*a['agi']+0.08*a['luk']+b.get('crit_rate',0))),
      'crit_damage':min(300,max(100,150+b.get('crit_damage',0))),
      'max_hp':max(1,int(50+5*a['vit']+10*(lv-1)+b.get('max_hp',0))),
      'max_mp':max(0,int(20+4*a['spi']+2*(lv-1)+b.get('max_mp',0))),
    }
    h=data['hidden_talents']
    result['magic_control']=h.get('magic_control',0)+0.3*a['spi']+0.1*a['int']+b.get('magic_control',0)
    result['magic_affinity']=h.get('magic_affinity',0)+b.get('magic_affinity',0)
    result['perception']=h.get('perception',0)+0.2*a['luk']+b.get('perception',0)
    result['willpower']=h.get('willpower',0)+0.2*a['vit']+0.2*a['spi']+b.get('willpower',0)
    result['loot_bonus']=min(0.35,max(0,0.002*a['luk']+b.get('loot_bonus',0)))
    result['element_affinity']={k:h.get('element_affinity',{}).get(k,0)+b.get(k+'_affinity',0) for k in AFFINITIES}
    return result

def synchronize(data, old_max=None):
    stats=calculate(data)
    if old_max is None:
        old_max=(int(data.get('max_hp',stats['max_hp'])),int(data.get('max_mp',stats['max_mp'])))
    for resource,old in (('hp',old_max[0]),('mp',old_max[1])):
        maximum=stats['max_'+resource]
        current=int(data.get(resource,maximum))
        # 保留已消耗的生命與魔力，避免換裝時直接回滿
        missing=max(0,old-current)
        data['max_'+resource]=maximum
        data[resource]=max(0,maximum-missing)
    return data

class CharacterProgression:
    def __init__(self):
        if not PLAYER.exists(): raise FileNotFoundError(str(PLAYER))
        self.data=ensure(read(PLAYER,{}))
        self.data=synchronize(self.data)
        self.save()
    def save(self): write(PLAYER,self.data)
    def reload(self):
        self.data=ensure(read(PLAYER,{}))
        return self.data
    def snapshot(self):
        self.reload()
        return {'player':copy.deepcopy(self.data),'stats':calculate(self.data)}
    def allocate(self,key,amount=1):
        self.reload()
        if key not in STATS or not isinstance(amount,int) or amount<=0: return False
        if self.data['unspent_points']<amount: return False
        old=(self.data['max_hp'],self.data['max_mp'])
        self.data['base_stats'][key]+=amount
        self.data['unspent_points']-=amount
        self.data['allocated_points']+=amount
        synchronize(self.data,old)
        self.save()
        return True
    def gain_exp(self,amount):
        if not isinstance(amount,int) or amount<0: raise ValueError('經驗值必須為非負整數')
        self.reload(); old=(self.data['max_hp'],self.data['max_mp'])
        self.data['exp']+=amount
        levels=0
        while self.data['exp']>=self.data['exp_to_next_level']:
            self.data['exp']-=self.data['exp_to_next_level']
            self.data['level']+=1
            self.data['unspent_points']+=5
            self.data['exp_to_next_level']=100*self.data['level']
            levels+=1
        synchronize(self.data,old)
        self.save()
        return levels
    def set_hidden_talent(self,key,value):
        # 供未來任務、技能與劇情事件呼叫；不提供玩家直接配點
        if key not in ('magic_control','magic_affinity','perception','willpower'):
            raise ValueError('未知隱藏天賦')
        self.reload()
        self.data['hidden_talents'][key]=value
        self.save()
