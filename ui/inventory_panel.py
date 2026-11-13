"""Actual clickable inventory UI: five independent equipment slots + hotbar binding.
The old background template had a nonmatching return button and only two equipment boxes.
This panel uses the *same hit rectangles* for drawing and mouse input.
"""
from pathlib import Path
import pygame
from systems.inventory_manager import InventoryManager

ROOT=Path(__file__).resolve().parents[1]

class InventoryPanel:
    BASE_W,BASE_H=1100,620
    CATEGORIES=(('全部','all'),('消耗品','consumable'),('裝備','equipment'),('材料','material'))
    SLOT_NAMES={'weapon':'武器','armor':'防具','shoes':'鞋子','ring':'戒指','medal':'勳章'}
    SLOTS=tuple(SLOT_NAMES)
    def __init__(self):
        self.manager=InventoryManager()
        self.category='all'
        self.selected=None
        self.selected_equipment=None
        self.closed=False
        self.back_requested=False
        self.message=''
        self.rect=pygame.Rect(0,0,self.BASE_W,self.BASE_H)
        self.font_cache={}
        self.images={}
        self.quickbar=None
        self.areas={}
        self.hover=None
        self.template=None

    def font(self,size):
        if size not in self.font_cache:
            p=ROOT/'assets/fonts/NotoSansTC-Regular.ttf'
            self.font_cache[size]=pygame.font.Font(str(p) if p.is_file() else None,size)
        return self.font_cache[size]

    def items(self):
        result=[]
        for item in self.manager.data.get('items',[]):
            info=self.manager.database.get(item.get('item_id'),{})
            if self.category=='all' or (self.category=='equipment' and info.get('slot') in self.SLOTS) or info.get('type')==self.category:
                result.append(item)
        return result

    def icon(self,item_id,size):
        key=(item_id,size)
        if key in self.images:return self.images[key]
        info=self.manager.get_item_info(item_id)
        rel=info.get('icon','')
        p=ROOT/rel
        if not rel or not p.exists():return None
        image=pygame.image.load(str(p)).convert_alpha()
        image=pygame.transform.scale(image,(size,size))
        self.images[key]=image
        return image

    def _text(self,surf,text,x,y,size=20,color=(247,234,208),max_w=None):
        f=self.font(size);words=str(text)
        if max_w:
            while words and f.size(words)[0]>max_w:words=words[:-1]
        if words:surf.blit(f.render(words,True,color),(int(x),int(y)))

    def _box(self,surf,r,fill=(48,42,72),edge=(151,126,98),selected=False):
        pygame.draw.rect(surf,fill,r,border_radius=7)
        pygame.draw.rect(surf,(244,196,105) if selected else edge,r,3 if selected else 2,border_radius=7)

    def _button(self,surf,name,rect):
        hovered=self.hover==('button',name)
        self._box(surf,rect,(98,69,106) if hovered else (65,54,87),selected=hovered)
        font=self.font(21)
        label=font.render(name,True,(250,227,190))
        surf.blit(label,label.get_rect(center=rect.center))
        self.areas[('button',name)]=rect

    def render_canvas(self):
        surf=pygame.Surface((self.BASE_W,self.BASE_H),pygame.SRCALPHA)
        surf.fill((27,28,49,248))
        pygame.draw.rect(surf,(222,175,98),(4,4,self.BASE_W-8,self.BASE_H-8),3,border_radius=12)
        self.areas={}
        self._text(surf,'魔法學院冒險背包',191,36,29,(255,223,151))
        back=pygame.Rect(28,24,142,47)
        self._box(surf,back,(70,53,92));self._text(surf,'〈返回選單',39,34,20)
        self.areas[('back',None)]=back
        close=pygame.Rect(968,24,102,47)
        self._box(surf,close,(93,51,75));self._text(surf,'關閉 ×',976,33,20)
        self.areas[('close',None)]=close
        for i,(title,cat) in enumerate(self.CATEGORIES):
            r=pygame.Rect(32+i*137,96,126,42)
            self._box(surf,r,(80,65,105) if self.category==cat else (53,49,75),selected=self.category==cat)
            self._text(surf,title,r.x+17,r.y+8,19)
            self.areas[('category',cat)]=r
        self._text(surf,f'容量：{len(self.manager.data["items"])} / {self.manager.data.get("capacity",20)}',563,101,19,(181,207,214))
        entries=self.items()
        for idx in range(20):
            r=pygame.Rect(33+(idx%5)*106,157+(idx//5)*91,92,82)
            self._box(surf,r,selected=self.selected==idx)
            self.areas[('slot',idx)]=r
            if idx>=len(entries):continue
            entry=entries[idx];item_id=entry['item_id']
            image=self.icon(item_id,56)
            if image:surf.blit(image,image.get_rect(center=r.center))
            amount=int(entry.get('amount',1))
            if amount>1:self._text(surf,str(amount),r.right-23,r.bottom-21,16)
        selected_info=None
        if self.selected is not None and self.selected<len(entries):
            entry=entries[self.selected];selected_info=self.manager.get_item_info(entry['item_id'])
            self._box(surf,pygame.Rect(565,157,164,353),(35,34,57))
            img=self.icon(entry['item_id'],96)
            if img:surf.blit(img,(596,174))
            self._text(surf,selected_info.get('name','物品'),579,286,20,max_w=139)
            self._text(surf,'持有 '+str(entry.get('amount',1)),580,324,17)
            desc=selected_info.get('description','')
            # Chinese multi-line by characters, not long text truncation to one line.
            lines=['']
            for ch in desc:
                if self.font(16).size(lines[-1]+ch)[0]>142:lines.append('')
                lines[-1]+=ch
            for i,line in enumerate(lines[:4]):self._text(surf,line,577,365+i*24,16,(220,217,202))
            bonuses=selected_info.get('bonuses',{})
            for i,(stat,val) in enumerate(list(bonuses.items())[:3]):
                self._text(surf,f'{stat}: +{val}',580,444+i*20,15,(229,202,128))
        else:
            self._box(surf,pygame.Rect(565,157,164,353),(35,34,57))
            self._text(surf,'選擇物品',582,290,20)
        self._text(surf,'裝 備 欄',781,99,22,(249,219,151))
        for i,slot in enumerate(self.SLOTS):
            box=pygame.Rect(747,145+i*75,324,66)
            self._box(surf,box,(59,50,77),selected=self.selected_equipment==slot)
            self.areas[('equipment',slot)]=box
            item_id=self.manager.get_equipped_item(slot)
            name=self.manager.get_item_info(item_id).get('name','未裝備') if item_id else '未裝備'
            self._text(surf,self.SLOT_NAMES[slot],box.x+13,box.y+8,20,(249,205,132))
            self._text(surf,name,box.x+111,box.y+8,20,max_w=192)
            if item_id:
                image=self.icon(item_id,39)
                if image:surf.blit(image,(box.x+54,box.y+14))
            self._text(surf,'點選欄位可卸下',box.x+116,box.y+38,14,(183,190,209))
        for i,name in enumerate(('使用道具','裝備','卸下','設到快捷列')):
            self._button(surf,name,pygame.Rect(35+i*177,541,166,48))
        self._text(surf,self.message or '選擇物品後使用 / 裝備；選擇裝備欄後卸下。',746,547,16,(231,207,146),max_w=334)
        self._text(surf,'快捷列綁定：選中道具後按 1～6；Esc 返回選單、Tab 返回遊戲',32,595,15,(173,183,211))
        return surf

    def draw(self,screen,rect=None):
        if self.closed:return
        if rect is not None:self.rect=pygame.Rect(rect)
        canvas=self.render_canvas()
        image=pygame.transform.scale(canvas,self.rect.size)
        screen.blit(image,self.rect.topleft)

    def get_hit(self,screen_pos):
        if not self.rect.collidepoint(screen_pos):return None
        pt=((screen_pos[0]-self.rect.x)*self.BASE_W/self.rect.width,
            (screen_pos[1]-self.rect.y)*self.BASE_H/self.rect.height)
        # Areas are reconstructed by draw(). If a click comes before draw, prepare them.
        if not self.areas:self.render_canvas()
        for hit,r in self.areas.items():
            if r.collidepoint(pt):return hit
        return None

    def perform(self,name):
        if name=='卸下':
            if self.selected_equipment is None:
                self.message='請先點選右側的裝備欄';return True
            self.manager.unequip_item(self.selected_equipment)
            self.message=self.manager.last_message
            return True
        entries=self.items()
        if self.selected is None or self.selected>=len(entries):
            self.message='請先點選背包物品';return True
        item_id=entries[self.selected]['item_id'];info=self.manager.get_item_info(item_id)
        if name=='使用道具':
            self.manager.use_item(item_id)
            self.message=self.manager.last_message
        elif name=='裝備':
            self.manager.equip_item(item_id)
            self.message=self.manager.last_message
        elif name=='設到快捷列':
            if self.quickbar:
                self.quickbar.assign(0,item_id)
                self.message=self.quickbar.last_message+'（按 1 使用）'
            else:self.message='快捷列尚未載入'
        else:return False
        # On success item quantity or equipped slot may change.
        if self.selected>=len(self.items()):self.selected=None
        return True

    def handle_event(self,event,rect=None):
        if rect is not None:self.rect=pygame.Rect(rect)
        if event.type not in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEMOTION):return False
        hit=self.get_hit(event.pos)
        if event.type==pygame.MOUSEMOTION:
            self.hover=hit;return bool(hit)
        if event.button!=1 or not hit:return False
        kind,val=hit
        if kind=='back':self.back_requested=True;return True
        if kind=='close':self.closed=True;return True
        if kind=='category':
            self.category=val;self.selected=None;self.selected_equipment=None;self.message='';return True
        if kind=='equipment':
            self.selected_equipment=val;self.selected=None
            self.message=f'已選擇{self.SLOT_NAMES[val]}欄';return True
        if kind=='slot':
            self.selected=val if val<len(self.items()) else None
            self.selected_equipment=None;self.message='';return True
        if kind=='button':return self.perform(val)
        return True

    def handle_key(self,key):
        if key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):self.back_requested=True;return True
        if key==pygame.K_u:
            return self.perform('卸下')
        if key in (pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT):
            step={pygame.K_UP:-5,pygame.K_DOWN:5,pygame.K_LEFT:-1,pygame.K_RIGHT:1}[key]
            n=len(self.items())
            if n:self.selected=(0 if self.selected is None else (self.selected+step)%n)
            return True
        if key in (pygame.K_RETURN,pygame.K_e):
            entry=(self.items()[self.selected] if self.selected is not None and self.selected<len(self.items()) else None)
            return self.perform('使用道具' if entry and self.manager.get_item_info(entry['item_id']).get('type') in ('consumable','potion') else '裝備')
        if pygame.K_1<=key<=pygame.K_6:
            entries=self.items()
            if self.selected is None or self.selected>=len(entries):self.message='請先選擇一個消耗品';return True
            if self.quickbar:
                self.quickbar.assign(key-pygame.K_1,entries[self.selected]['item_id'])
                self.message=self.quickbar.last_message
            return True
        return False
