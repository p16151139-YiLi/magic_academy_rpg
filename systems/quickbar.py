"""Phase 8 V8: persistent 1-6 item hotbar, independent of the menu.
Actions are allowed only in the game world; merchant/dialogue panels take priority.
"""
from pathlib import Path
import pygame
from systems.inventory_manager import InventoryManager
from systems.save_store import read_json, write_json

ROOT=Path(__file__).resolve().parents[1]
HOTBAR=ROOT/'data/player/hotbar.json'

class Quickbar:
    KEYS=(pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5,pygame.K_6)
    def __init__(self):
        self.slots=read_json(HOTBAR,{'slots':['hp_potion_small','mp_potion_small',None,None,None,None]}).get('slots',[])
        self.slots=(self.slots+[None]*6)[:6]
        self.inventory=InventoryManager()
        self.images={}
        self.last_message=''
        self.notice_time=0
        self.font_path=ROOT/'assets/fonts/NotoSansTC-Regular.ttf'
        self.font_cache={}
        self.rects=[]
        self._refresh_interval=0.0
        self.save()

    def save(self):
        write_json(HOTBAR,{'slots':self.slots})

    def assign(self,index,item_id):
        if not 0<=index<6:return False
        info=self.inventory.database.get(item_id,{})
        if info.get('type') not in ('consumable','potion'):
            self.last_message='快捷列只能放可使用的道具';return False
        self.slots[index]=item_id;self.save()
        self.last_message=f'{info.get("name",item_id)} 已設定到快捷列 {index+1}'
        self.notice_time=2.5
        return True

    def unassign(self,index):
        if 0<=index<6:
            self.slots[index]=None;self.save();return True
        return False

    def use(self,index):
        if not 0<=index<6:return False
        item_id=self.slots[index]
        if not item_id:
            self.last_message='這個快捷欄尚未設定物品';self.notice_time=2.1;return False
        self.inventory.reload()
        success=self.inventory.use_item(item_id)
        self.last_message=self.inventory.last_message
        self.notice_time=2.2
        return success

    def icon(self,item_id,size):
        key=(item_id,size)
        if key in self.images:return self.images[key]
        info=self.inventory.database.get(item_id,{})
        path=ROOT/info.get('icon','')
        if not info.get('icon') or not path.is_file():return None
        img=pygame.image.load(str(path)).convert_alpha()
        img=pygame.transform.scale(img,(size,size))
        self.images[key]=img
        return img

    def font(self,size):
        if size not in self.font_cache:
            self.font_cache[size]=pygame.font.Font(str(self.font_path) if self.font_path.exists() else None,size)
        return self.font_cache[size]

    def update(self,dt):
        self.notice_time=max(0,self.notice_time-dt)
        self._refresh_interval-=dt
        if self._refresh_interval<=0:
            self.inventory.reload()
            self._refresh_interval=0.35

    def draw(self,screen):
        sw,sh=screen.get_size()
        slot=54 if sw>=1050 else 43
        gap=5
        width=6*slot+7*gap
        x=sw-width-14;y=sh-slot-14
        if y<0:return
        bg=pygame.Rect(x,y-13,width,slot+23)
        pygame.draw.rect(screen,(25,23,47),bg,border_radius=10)
        pygame.draw.rect(screen,(192,151,83),bg,2,border_radius=10)
        self.rects=[]
        for i,item_id in enumerate(self.slots):
            r=pygame.Rect(x+gap+i*(slot+gap),y,slot,slot)
            self.rects.append(r)
            pygame.draw.rect(screen,(51,45,78),r,border_radius=5)
            pygame.draw.rect(screen,(166,142,98),r,2,border_radius=5)
            if item_id:
                img=self.icon(item_id,slot-14)
                if img:screen.blit(img,img.get_rect(center=r.center))
                count=self.inventory.get_item_count(item_id)
                cnt=self.font(14).render(str(count),True,(250,229,185))
                screen.blit(cnt,cnt.get_rect(bottomright=(r.right-3,r.bottom-2)))
            key_label=self.font(14).render(str(i+1),True,(255,237,183))
            screen.blit(key_label,(r.x+4,r.y+2))
        if self.notice_time>0 and self.last_message:
            label=self.font(18).render(self.last_message,True,(255,232,186))
            bubble=label.get_rect(bottomright=(sw-17,y-19)).inflate(20,12)
            pygame.draw.rect(screen,(31,27,49),bubble,border_radius=6)
            screen.blit(label,label.get_rect(center=bubble.center))

    def click(self,pos):
        for i,rect in enumerate(self.rects):
            if rect.collidepoint(pos):
                self.use(i)
                return True
        return False
