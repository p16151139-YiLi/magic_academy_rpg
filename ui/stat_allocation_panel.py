
import pygame
from pathlib import Path
from systems.character_progression import CharacterProgression, STATS
ROOT=Path(__file__).resolve().parents[1]
LABELS={'str':'力量','vit':'體質','int':'智力','spi':'精神','agi':'敏捷','luk':'幸運'}
class StatAllocationPanel:
    def __init__(self):
        self.progress=CharacterProgression()
        self.buttons={}
        self.fonts={}
        self.message=''
    def font(self,size):
        if size not in self.fonts:
            p=ROOT/'assets/fonts/NotoSansTC-Regular.ttf'
            self.fonts[size]=pygame.font.Font(str(p) if p.exists() else None,size)
        return self.fonts[size]
    def label(self,surf,text,pos,size=18,color=(240,233,211)):
        surf.blit(self.font(size).render(str(text),True,color),pos)
    def draw(self,surface,rect):
        snap=self.progress.snapshot(); data=snap['player']; st=snap['stats']
        r=pygame.Rect(rect)
        panel=pygame.Surface(r.size,pygame.SRCALPHA)
        panel.fill((21,29,48,246))
        pygame.draw.rect(panel,(177,143,83),panel.get_rect(),2,border_radius=8)
        self.label(panel,f"{data.get('name','冒險者')}  Lv.{data['level']}  {data.get('class_name','')}",(18,9),19,(255,211,129))
        self.label(panel,f"HP {data['hp']}/{st['max_hp']}    MP {data['mp']}/{st['max_mp']}    EXP {data['exp']}/{data['exp_to_next_level']}",(18,40),16)
        self.label(panel,f"可分配點數：{data['unspent_points']}  （每級 +5）",(18,66),17,(255,217,139))
        self.buttons={}
        for i,key in enumerate(STATS):
            col,row=i%3,i//3
            x=18+col*int((r.width-36)/3)
            y=98+row*42
            self.label(panel,f"{LABELS[key]} {data['base_stats'][key]}",(x,y+5),17)
            button=pygame.Rect(x+112,y,27,27)
            pygame.draw.rect(panel,(69,111,92) if data['unspent_points'] else (70,72,78),button,border_radius=5)
            self.label(panel,'+', (button.x+7,button.y),19)
            self.buttons[key]=button.move(r.topleft)
        self.label(panel,'物攻 {:g}  魔攻 {:g}  物防 {:g}  魔防 {:g}'.format(st['physical_attack'],st['magic_attack'],st['physical_defense'],st['magic_defense']),(18,191),16)
        self.label(panel,'暴擊率 {:.1f}%   暴擊傷害 {:.1f}%'.format(st['crit_rate'],st['crit_damage']),(18,216),16)
        self.label(panel,self.message or '點擊 + 分配能力點數',(18,248),15,(240,203,143))
        surface.blit(panel,r.topleft)
    def handle_event(self,event):
        if event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1: return False
        for key,rect in self.buttons.items():
            if rect.collidepoint(event.pos):
                ok=self.progress.allocate(key)
                self.message=('已提升'+LABELS[key]) if ok else '沒有可分配的點數'
                return True
        return False
