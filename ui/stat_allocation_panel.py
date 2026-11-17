"""Compact character overview for PlayerMenu tab 0.

Direct-to-display rendering keeps pygame/pygbag texture allocation bounded.
All displayed data comes from the same CharacterProgression snapshot as upgrades.
"""
from pathlib import Path
import pygame
from systems.character_progression import CharacterProgression, STATS
ROOT = Path(__file__).resolve().parents[1]
LABELS={'str':'力量','vit':'體質','int':'智力','spi':'精神','agi':'敏捷','luk':'幸運'}
PORTRAITS={
 'balanced_mage':'balanced_mage_portrait.png',
 'melee_mage':'melee_mage_portrait.png',
 'ranged_mage':'ranged_mage_portrait.png',
}

class StatAllocationPanel:
    def __init__(self):
        self.progress=CharacterProgression()
        self.buttons={}
        self.fonts={}
        self._text_cache={}
        self._portrait_cache={}
        self.message=''
        self._snapshot_cache = None

    def invalidate(self):
        self._snapshot_cache = None

    def snapshot(self):
        # Opening or updating the panel invalidates this; avoid allocating
        # new nested dicts and reloading saves on every video frame.
        if self._snapshot_cache is None:
            self._snapshot_cache = self.progress.snapshot()
        return self._snapshot_cache
    def font(self,size):
        size=max(12,int(size))
        if size not in self.fonts:
            path=ROOT/'assets/fonts/NotoSansTC-Regular.ttf'
            self.fonts[size]=pygame.font.Font(str(path) if path.is_file() else None,size)
        return self.fonts[size]
    def label(self,surface,value,pos,size=16,color=(241,234,214)):
        key=(str(value),int(size),tuple(color))
        glyph=self._text_cache.get(key)
        if glyph is None:
            glyph=self.font(size).render(str(value),True,color)
            if len(self._text_cache)>=160:self._text_cache.clear()
            self._text_cache[key]=glyph
        surface.blit(glyph,(int(pos[0]),int(pos[1])))
    def portrait(self,class_id):
        if class_id not in self._portrait_cache:
            filename=PORTRAITS.get(class_id)
            path=(ROOT/'assets/characters/portraits'/filename) if filename else None
            result=None
            if path is not None and path.is_file():
                try:
                    loaded=pygame.image.load(str(path))
                    if pygame.display.get_surface() is not None:
                        loaded=loaded.convert_alpha()
                    result=pygame.transform.smoothscale(loaded,(102,102))
                except (pygame.error,ValueError,OSError) as exc:
                    print('[CHARACTER PORTRAIT ERROR]',path,repr(exc),flush=True)
            self._portrait_cache[class_id]=result
        return self._portrait_cache[class_id]
    def draw(self,surface,rect):
        r=pygame.Rect(rect)
        if r.width < 600 or r.height < 220:
            raise ValueError('Character panel needs at least 600x220, got '+repr(r.size))
        snap=self.snapshot()
        data=snap['player'];stat=snap['stats']
        # No temporary Surface and no surface.set_alpha(): draw in-place every frame.
        pygame.draw.rect(surface,(28,32,53),r,border_radius=8)
        pygame.draw.rect(surface,(177,143,83),r,2,border_radius=8)
        x,y=r.topleft
        self.label(surface,f"{data.get('name','冒險者')}    Lv.{data['level']}    {data.get('class_name','')}",
                   (x+140,y+8),19,(255,218,142))
        pygame.draw.rect(surface,(47,51,74),(x+15,y+33,110,111),border_radius=5)
        portrait=self.portrait(data.get('class_id','balanced_mage'))
        if portrait is not None:surface.blit(portrait,(x+19,y+37))
        else:self.label(surface,'角色', (x+46,y+82),18)
        self.label(surface,f"金幣：{data.get('gold',0)}",(x+19,y+154),17,(255,222,151))
        self.label(surface,f"可分配：{data.get('unspent_points',0)}",(x+19,y+180),16,(255,220,140))
        def bar(yy,title,current,maximum,color):
            self.label(surface,f'{title}  {current}/{maximum}',(x+143,y+yy),15)
            bx=x+354;by=y+yy+4;bw=168;bh=12
            pygame.draw.rect(surface,(16,19,35),(bx,by,bw,bh),border_radius=3)
            value=max(0,min(bw,round(bw*float(current)/max(1,float(maximum)))))
            if value>0:pygame.draw.rect(surface,color,(bx,by,value,bh),border_radius=3)
            pygame.draw.rect(surface,(122,126,151),(bx,by,bw,bh),1,border_radius=3)
        bar(40,'HP',data.get('hp',0),stat['max_hp'],(207,83,98))
        bar(66,'MP',data.get('mp',0),stat['max_mp'],(84,139,222))
        bar(92,'EXP',data.get('exp',0),data.get('exp_to_next_level',100),(124,185,118))
        self.label(surface,'屬性配點', (x+141,y+122),16,(242,211,154))
        self.buttons={}
        for i,key in enumerate(STATS):
            col=i%3;row=i//3
            sx=x+143+col*211;sy=y+147+row*30
            self.label(surface,f"{LABELS[key]} {data['base_stats'][key]}",(sx,sy),15)
            btn=pygame.Rect(sx+103,sy,24,23)
            pygame.draw.rect(surface,(62,104,80) if data.get('unspent_points',0) else (70,72,78),btn,border_radius=4)
            self.label(surface,'+',(btn.x+6,btn.y),17)
            self.buttons[key]=btn
        self.label(surface,
          '物攻 {:g}    魔攻 {:g}    物防 {:g}    魔防 {:g}'.format(
            stat['physical_attack'],stat['magic_attack'],stat['physical_defense'],stat['magic_defense']),
          (x+145,y+208),14,(218,221,236))
        if self.message:
            self.label(surface,self.message,(x+570,y+99),14,(255,212,140))
    def handle_event(self,event):
        if event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1:return False
        for key,rect in self.buttons.items():
            if rect.collidepoint(event.pos):
                result=self.progress.allocate(key)
                self.invalidate()
                self.message=('已提升'+LABELS[key]) if result else '沒有可分配的點數'
                return True
        return False
