"""Phase 8: real AI-generated sprites, offline dynamic NPCs, and synced shops.
No procedural character drawings; game logic handles AI, interaction and inventory.
"""
import json
from pathlib import Path
import pygame
from systems.npc_ai.ai_controller import Agent
from systems.npc_sprite_library import NPCSpriteLibrary
from systems.save_store import read_json, write_json

ROOT=Path(__file__).resolve().parents[1]
WORLD_PATH=ROOT/'data/player/world_state.json'

class NPCShopSystem:
    GOODS={
      'item_shop':[('hp_potion_small',30),('mp_potion_small',40),('mana_crystal',35),('mana_ring',125),('academy_medal',145)],
      'weapon_shop':[('apprentice_staff',120),('magic_blade',180),('apprentice_robe',100),('academy_boots',85)],
    }
    SHOP_NAMES={'item_shop':'星露雜貨店','weapon_shop':'赤鐵武器鋪'}

    def __init__(self,scene):
        self.scene=scene
        self.agents={}
        self.positions={}
        self.dialogue=None
        self.shop=None
        self.selected=0
        self.notice=''
        self.notice_timer=0
        self.font=scene.ctx.font_small
        self.sprites=NPCSpriteLibrary()
        self.quests=read_json(WORLD_PATH,{'ancient_record':False})
        # Bundle source stays fixed even if tests redirect save ROOT to a temp folder.
        profile_file=Path(__file__).resolve().parents[1]/'data/npcs/dialogue_profiles.json'
        self.dialogue_profiles=json.loads(profile_file.read_text(encoding='utf-8'))['profiles']
        self.time=0.0
        self.item_service=scene.get_item_service()
        self.item_service.grant_starting_gold_once()
        self.icons={}
        self.click_rows=[]
        self.close_rect=pygame.Rect(0,0,0,0)
        self.buy_rect=pygame.Rect(0,0,0,0)
        self._fade_cache={}
        self._occluder_masks={}
        try:
            self._actor_mask=pygame.mask.Mask((58,93),fill=True)
        except Exception:
            # pygame.mask unavailable in a minimal test shim or browser.
            self._actor_mask=None

    def npcs(self):
        return [n for n in self.scene.map_data.get('npcs',[])
                if not n.get('requires_quest') or self.quests.get(n['requires_quest'])]

    def agent(self,npc):
        key=self.scene.map_id,npc['id']
        if key not in self.agents:
            self.agents[key]=Agent(npc,self.scene.map_id,npc['position'])
        return self.agents[key]

    def pos(self,npc):
        if npc.get('behavior')=='utility':
            return self.agent(npc).pos
        return pygame.Vector2(npc['position'])

    def npc_obstacles(self):
        # Seated characters already occupy furniture/benches drawn in the map.
        # Duplicating a collision around their chair blocks otherwise open aisles.
        return [pygame.Rect(round(self.pos(n).x-10),round(self.pos(n).y-6),20,13)
                for n in self.npcs() if n.get('pose') != 'sit']

    def update(self,dt):
        self.time+=dt
        self.notice_timer=max(0,self.notice_timer-dt)
        if self.dialogue or self.shop or self.scene.player_menu.opened:return
        current=self.npcs()
        agents=[self.agent(n) for n in current if n.get('behavior')=='utility']
        obstacles=self.scene.player_world.get_obstacles()
        # Free-roaming NPCs do not wander onto doorway thresholds or crowd
        # students already sitting on benches, desks or reading chairs.
        for exit_data in self.scene.map_manager.get_exits():
            rect=self.scene.player_world.get_exit_rect(exit_data)
            if rect:
                obstacles.append(rect.inflate(26, 25))
        for npc in current:
            if npc.get('behavior') != 'utility':
                p=self.pos(npc)
                size=(48, 36) if npc.get('pose') == 'sit' else (26, 20)
                obstacles.append(pygame.Rect(round(p.x-size[0]/2),round(p.y-size[1]/2),*size))
        bounds=pygame.Rect(0,0,self.scene.map_data['width'],self.scene.map_data['height'])
        player=pygame.Vector2(self.scene.player.rect.center)
        for agent in agents:
            agent.update(dt,obstacles,bounds,player,agents)

    def nearby(self):
        player=pygame.Vector2(self.scene.player.rect.center)
        options=[]
        for npc in self.npcs():
            d=player.distance_to(self.pos(npc))
            radius=float(npc.get('interaction_radius',95))
            if d<radius:
                # closer by relative interaction range; merchants behind counters remain accessible
                options.append((d/max(1,radius),d,npc))
        return min(options,key=lambda item:(item[0],item[1]))[2] if options else None

    def _profile(self, npc):
        return self.dialogue_profiles.get(npc.get('dialogue_profile',npc['id']), {})

    def _activity(self, npc):
        """Return what the NPC is ACTUALLY doing now, never a scripted guess.

        Movement and intent are observable Agent state. Static workers declare
        a map-specific activity that matches their standing/seated sprite.
        """
        if npc.get('behavior') == 'utility':
            agent=self.agent(npc)
            if agent.moving:
                return 'patrol' if npc.get('role') in ('guard','patrol') else 'walk'
            intent=agent.intent
            if intent == 'explore' and agent.route:
                return 'walk'
            if intent == 'explore':
                return 'idle'
            if intent == 'social' and npc.get('role') in ('guard','patrol'):
                return 'observe'
            return intent if intent in ('rest','observe','social','review','idle') else 'idle'
        return npc.get('activity','idle')

    def _activity_line(self, npc, activity):
        profile=self._profile(npc)
        activities=profile.get('activity',{})
        return (activities.get(activity) or activities.get('idle')
                or next(iter(activities.values()), '我正在處理自己手邊的事。'))

    def _conversation_choices(self, npc):
        profile=self._profile(npc)
        choices=profile.get('choices')
        if choices:
            return [(str(label),str(action)) for label,action in choices]
        return [('你現在在忙什麼？','activity'),('最近有什麼消息？','rumor'),('再見','leave')]

    def _reply_text(self,npc,action,activity):
        if action=='activity':
            return self._activity_line(npc,activity)
        reply=self._profile(npc).get('replies',{}).get(action)
        if isinstance(reply,dict):
            return (reply.get(activity) or reply.get('default')
                    or self._activity_line(npc,activity))
        if isinstance(reply,str) and reply:
            return reply
        return self._activity_line(npc,activity)

    def _choose_dialogue(self):
        d=self.dialogue
        if d is None:
            return
        npc=d['npc']
        choices=self._conversation_choices(npc)
        selected=min(max(d.get('selected',0),0),len(choices)-1)
        _,action=choices[selected]
        if action=='leave':
            self.dialogue=None
            return
        if action=='shop':
            self.dialogue=None
            self.shop=npc.get('shop')
            self.selected=0
            self.notice=''
            return
        if action=='quest':
            already=self.quests.get('ancient_record',False)
            if not already:
                self.quests['ancient_record']=True
                write_json(WORLD_PATH,self.quests)
                text='謝謝你願意協助調查。請到一樓圖書館尋找古代魔法的記錄。'
            else:
                text='調查還在進行中。請先到圖書館尋找線索，再回來告訴我。'
        else:
            # The activity is captured at the start of interaction. An NPC
            # does not suddenly claim to be walking while the dialogue freezes it.
            text=self._reply_text(npc,action,d.get('activity','idle'))
        d['mode']='reply'
        d['reply']=text

    def interact(self):
        if self.shop:
            return True
        if self.dialogue:
            d = self.dialogue
            if d['mode'] == 'lines':
                d['index'] += 1
                if d['index'] >= len(d['lines']):
                    d['mode'] = 'choices'
                    d['selected'] = 0
            elif d['mode'] == 'choices':
                self._choose_dialogue()
            else:
                d['mode'] = 'choices'
            return True
        npc = self.nearby()
        if npc is None:
            return False
        activity=self._activity(npc)
        profile=self._profile(npc)
        intro=profile.get('greeting') or (npc.get('dialogue') or ['你好。'])[0]
        detail=self._activity_line(npc,activity)
        # 2 context-matched lines only, so the dialogue panel stays readable.
        lines=[intro,detail] if detail!=intro else [intro]
        if npc.get('behavior') == 'utility':
            moving_agent=self.agent(npc)
            moving_agent.pause_for_dialogue(
                pygame.Vector2(self.scene.player.rect.center))
        self.dialogue = {'npc': npc, 'index': 0, 'lines': lines,
                         'activity':activity,
                         'selected': 0, 'mode': 'lines', 'reply': ''}
        self.shop = None
        return True

    def buy_selected(self):
        if not self.shop:return False
        item_id,price=self.GOODS[self.shop][self.selected]
        result=self.item_service.buy_item(item_id,price)
        self.notice=result['message'];self.notice_timer=2.4
        self.scene.player_world.show_message(result['message'])
        if result['success']:
            # Same InventoryManager object is shared by bag UI and shop.
            self.scene.player_menu.inventory_panel.manager.reload()
        return result['success']

    def handle_key(self, key):
        if self.dialogue:
            d = self.dialogue
            if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_TAB):
                self.dialogue = None
            elif d['mode'] == 'choices' and key in (pygame.K_DOWN, pygame.K_s):
                d['selected'] = (d['selected'] + 1) % len(self._conversation_choices(d['npc']))
            elif d['mode'] == 'choices' and key in (pygame.K_UP, pygame.K_w):
                d['selected'] = (d['selected'] - 1) % len(self._conversation_choices(d['npc']))
            elif d['mode'] == 'choices' and key in (pygame.K_1, pygame.K_2, pygame.K_3):
                d['selected'] = min(key-pygame.K_1, len(self._conversation_choices(d['npc']))-1)
                self._choose_dialogue()
            elif key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                self.interact()
            return True
        if not self.shop:
            return False
        goods = self.GOODS[self.shop]
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_TAB):
            self.shop = None
            self.notice = ''
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(goods)
        elif key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(goods)
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.selected = min(len(goods)-1, (key-pygame.K_1))
        elif key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            self.buy_selected()
        return True

    def handle_event(self,event):
        if not self.shop and not self.dialogue:
            return False
        if event.type == pygame.MOUSEWHEEL and self.shop:
            self.selected = (self.selected - event.y) % len(self.GOODS[self.shop])
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.dialogue:
            if self.close_rect.collidepoint(event.pos):
                self.dialogue = None
                return True
            if self.dialogue['mode'] == 'choices':
                for i,rect in enumerate(self.click_rows):
                    if rect.collidepoint(event.pos):
                        self.dialogue['selected'] = i
                        self._choose_dialogue()
                        return True
            else:
                self.interact()
            return True
        if self.close_rect.collidepoint(event.pos):
            self.shop = None
            self.notice = ''
            return True
        if self.buy_rect.collidepoint(event.pos):
            self.buy_selected()
            return True
        for i,rect in enumerate(self.click_rows):
            if rect.collidepoint(event.pos):
                self.selected = i
                return True
        return True

    def _item_icon(self,item_id,size=56):
        key=item_id,size
        if key in self.icons:return self.icons[key]
        db=self.item_service.inventory.database.get(item_id,{})
        path=ROOT/db.get('icon','')
        if not db.get('icon') or not path.is_file():return None
        image=pygame.image.load(str(path)).convert_alpha()
        image=pygame.transform.scale(image,(size,size))
        self.icons[key]=image
        return image

    def draw_npcs(self, screen, include_player=False):
        ox,oy=self.scene.camera.x,self.scene.camera.y
        who=self.nearby() if not self.shop and not self.dialogue else None
        # Actor bodies are used for soft camera occlusion. When a real shelf or
        # column obscures an actor, its foreground sprite fades instead of
        # cutting off the character's head or shoes abruptly.
        actor_boxes = [pygame.Rect(round(self.scene.player.rect.centerx-29),
                                   round(self.scene.player.rect.bottom-91),58,93)]
        # Seated workers are intentionally BEHIND the counter/table in the
        # underlying art. Do not make that furniture ghostly simply because
        # their torso is behind it; this avoids the missing-legs visual bug.
        for n in self.npcs():
            if n.get('pose') == 'sit':
                continue
            # Actual nontransparent character pixels, not an arbitrary 58x92
            # rectangle that can fade nearby shelves prematurely.
            atlas = self.sprites.frames(n['sprite'])
            visual = atlas[0][0].get_bounding_rect(min_alpha=25)
            if visual.w <= 0 or visual.h <= 0:
                continue
            position = self.pos(n)
            actor_boxes.append(pygame.Rect(
                round(position.x - visual.w / 2),
                round(position.y - visual.h), visual.w, visual.h))
        # depth is feet position, never sprite top. Foreground objects join the
        # same sorted display list: standing BEHIND a shelf hides the body;
        # walking IN FRONT displays the actor over the shelf image.
        entities=[(float(n.get('draw_depth',self.pos(n).y+5)),0,'npc',n) for n in self.npcs()]
        if include_player:
            entities.append((self.scene.player.rect.bottom+7,0,'player',None))
        for depth,asset,x,y,fade_allowed in self.scene.map_renderer.occluders:
            entities.append((depth,1,'occluder',(asset,x,y,fade_allowed)))
        entities.sort(key=lambda pair:(pair[0],pair[1]))
        for draw_depth,layer_order,kind,payload in entities:
            if kind == 'player':
                self.scene.player.draw(screen,camera_offset=(ox,oy))
                continue
            if kind == 'occluder':
                image,x,y,fade_allowed=payload
                area=pygame.Rect(x,y,*image.get_size())
                # Real alpha silhouette check: transparent corners of cropped
                # furniture must NOT trigger fading in empty floor tiles.
                key=id(image)
                object_mask=self._occluder_masks.get(key)
                # Objects are not erased or drawn as opaque rectangles over
                # people. Only pixels that actually overlap a sprite fade,
                # preserving the rest of a shelf / column at full opacity.
                # Bottom boundary walls remain solid and never become ghostly.
                fade_regions=[]
                is_boundary_wall = y >= 690 and image.get_width() >= 450
                if not is_boundary_wall and fade_allowed:
                    for b in actor_boxes:
                        # Only fade foreground props for actors whose feet are
                        # BEHIND the prop's lower depth, not actors in front.
                        if b.bottom > draw_depth + 24 or not area.colliderect(b):
                            continue
                        if self._actor_mask is not None and object_mask is None:
                            object_mask=pygame.mask.from_surface(image,60)
                            self._occluder_masks[key]=object_mask
                        if object_mask is not None:
                            actor_mask=pygame.mask.Mask(b.size,fill=True)
                            is_covered = object_mask.overlap_area(
                                actor_mask,(b.left-x,b.top-y)) > 55
                        else:
                            hit=area.clip(b)
                            sx=max(1,hit.width//9);sy=max(1,hit.height//9)
                            is_covered=any(image.get_at((ix-x,iy-y)).a>60
                                for ix in range(hit.left,hit.right,sx)
                                for iy in range(hit.top,hit.bottom,sy))
                        if is_covered:
                            fade_regions.append(area.clip(b.inflate(12,10)))
                if fade_regions:
                    # A localized RGBA alpha mask, not set_alpha() on a whole
                    # furniture sprite, avoids flickering of the entire shelf.
                    softened=image.copy()
                    for part in fade_regions:
                        local=pygame.Rect(part.x-x,part.y-y,part.w,part.h)
                        softened.fill((255,255,255,94),local,
                                      special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(softened,(round(x-ox),round(y-oy)))
                else:
                    screen.blit(image,(round(x-ox),round(y-oy)))
                continue
            npc=payload
            p=self.pos(npc);x,y=round(p.x-ox),round(p.y-oy)
            if not (-100<x<screen.get_width()+100 and -105<y<screen.get_height()+105):
                continue
            if npc.get('behavior')=='utility':
                agent=self.agent(npc)
                direction=agent.direction
                moving=agent.moving
                frame=int(agent.distance/11)%4 if moving else 0  # idle: no fake walking frame
                if self.dialogue and self.dialogue['npc'] is npc:
                    moving=False
                    frame=0  # No false 'walking in place' while speaking.
            else:
                # Fixed workers face their work; seated NPCs *never* stand up
                # or rotate through implausible walk frames during ambient idle.
                direction=npc.get('facing','down')
                if npc.get('face_player',True) and npc.get('pose') != 'sit':
                    pplayer=pygame.Vector2(self.scene.player.rect.center)
                    diff=pplayer-p
                    if diff.length_squared()<145**2:
                        if abs(diff.x)>abs(diff.y):
                            direction='right' if diff.x>0 else 'left'
                        else:
                            direction='down' if diff.y>0 else 'up'
                moving=False
                if npc.get('idle_animation'):
                    # Idle and speaking have different, intentional schedules:
                    # don't wave continuously when there is nobody to greet.
                    speaking=self.dialogue is not None and self.dialogue['npc'] is npc
                    if speaking and npc.get('talk_animation',False):
                        frame=2 if int(self.time*2.4)%2 else 0
                    else:
                        frame=1 if int(self.time*1.5)%13 == 0 else 0
                else:
                    frame=0  # No fake walking frames for standing workers.
            self.sprites.render(screen,npc['sprite'],direction,moving,frame,x,y,
                                npc.get('sprite_scale',1.0))
            if who is npc:
                label=self.font.render(npc['name']+'  E 交談',True,(250,232,185))
                bg=label.get_rect(midbottom=(x,y-(92 if npc.get('pose')=='sit' else 100))).inflate(16,10)
                pygame.draw.rect(screen,(28,27,49),bg,border_radius=5)
                pygame.draw.rect(screen,(198,165,99),bg,1,border_radius=5)
                screen.blit(label,label.get_rect(center=bg.center))

    def _draw_wrapped(self,screen,text,pos,width,color):
        # Chinese text wraps by rendered pixel width, not English word count.
        x,y=pos; line=''
        for char in str(text):
            candidate=line+char
            if self.font.size(candidate)[0]>width and line:
                screen.blit(self.font.render(line,True,color),(x,y))
                y+=self.font.get_linesize()+4; line=char
            else: line=candidate
        if line: screen.blit(self.font.render(line,True,color),(x,y))

    def draw_overlay(self, screen):
        if not self.shop and not self.dialogue:
            self.click_rows = []
            return
        sw, sh = screen.get_size()
        self.click_rows = []
        if self.dialogue:
            d = self.dialogue
            mode = d['mode']
            panel = pygame.Rect((sw-800)//2, sh-314, 800, 279)
            pygame.draw.rect(screen, (24, 27, 47), panel, border_radius=11)
            pygame.draw.rect(screen, (222, 177, 100), panel, 3, border_radius=11)
            npc = d['npc']
            profile=self._profile(npc)
            descriptor=profile.get('label',str(npc.get('role','NPC')))
            header = self.font.render(npc['name']+'  ·  '+descriptor, True, (251, 218, 155))
            screen.blit(header, (panel.x+25, panel.y+15))
            self.close_rect = pygame.Rect(panel.right-114, panel.y+14, 95, 37)
            pygame.draw.rect(screen, (89, 75, 103), self.close_rect, border_radius=6)
            close_label = self.font.render('返回 Esc', True, (249, 227, 195))
            screen.blit(close_label, close_label.get_rect(center=self.close_rect.center))
            if mode == 'lines':
                msg = d['lines'][min(d['index'], len(d['lines'])-1)]
                tip = 'E / Enter / 點擊：下一句    Esc / Tab：關閉對話'
                self._draw_wrapped(screen,msg,(panel.x+29,panel.y+93),panel.width-59,(245,240,234))
                screen.blit(self.font.render(tip, True, (180, 193, 216)), (panel.x+29,panel.bottom-49))
            elif mode == 'reply':
                msg = d['reply']
                self._draw_wrapped(screen,msg,(panel.x+29,panel.y+96),panel.width-60,(246,235,216))
                screen.blit(self.font.render('E / Enter：返回選項', True, (187, 204, 222)), (panel.x+29,panel.bottom-48))
            else:
                options = self._conversation_choices(npc)
                for i,(text,_) in enumerate(options):
                    rect = pygame.Rect(panel.x+27, panel.y+68+i*57, panel.width-54, 49)
                    self.click_rows.append(rect)
                    pygame.draw.rect(screen, (86, 68, 109) if i==d['selected'] else (44, 47, 70),rect,border_radius=7)
                    if i==d['selected']:
                        pygame.draw.rect(screen,(236,192,100),rect,2,border_radius=7)
                    label=self.font.render(f'{i+1}.  {text}', True, (255, 239, 204))
                    screen.blit(label,(rect.x+18,rect.y+9))
                screen.blit(self.font.render('↑↓ 選擇 / Enter 確認 / Esc / Tab 關閉', True,(187,204,222)),
                            (panel.x+29,panel.bottom-26))
            return
        panel = pygame.Rect((sw-780)//2,max(4,(sh-660)//2),780,min(sh-8,660))
        pygame.draw.rect(screen,(25,27,47),panel,border_radius=13)
        pygame.draw.rect(screen,(218,175,99),panel,3,border_radius=13)
        gold=self.item_service.get_player().get('gold',0)
        title=self.font.render(self.SHOP_NAMES[self.shop]+'    金幣：'+str(gold)+' G',True,(251,216,148))
        screen.blit(title,(panel.x+30,panel.y+21))
        for i,(item_id,price) in enumerate(self.GOODS[self.shop]):
            info=self.item_service.inventory.database.get(item_id,{})
            rect=pygame.Rect(panel.x+32,panel.y+74+i*76,716,70)
            self.click_rows.append(rect)
            pygame.draw.rect(screen,(91,70,112) if i==self.selected else (39,41,67),rect,border_radius=8)
            if i==self.selected:pygame.draw.rect(screen,(248,210,123),rect,3,border_radius=8)
            icon=self._item_icon(item_id,50)
            if icon:screen.blit(icon,(rect.x+18,rect.y+11))
            name=self.font.render(f'{i+1}. {info.get("name",item_id)}    {price} G',True,(247,227,179))
            desc=self.font.render(info.get('description',''),True,(216,218,233))
            owned=self.item_service.inventory.get_item_count(item_id)
            qty=self.font.render('背包持有：'+str(owned),True,(169,211,192))
            screen.blit(name,(rect.x+86,rect.y+4))
            screen.blit(desc,(rect.x+86,rect.y+30))
            screen.blit(qty,(rect.x+530,rect.y+40))
        self.buy_rect=pygame.Rect(panel.x+375,panel.bottom-86,215,45)
        self.close_rect=pygame.Rect(panel.x+606,panel.bottom-86,138,45)
        for rect,text,color in ((self.buy_rect,'購買選取商品',(94,84,135)),
                                (self.close_rect,'返回地圖 Esc',(80,66,97))):
            pygame.draw.rect(screen,color,rect,border_radius=7)
            pygame.draw.rect(screen,(209,174,109),rect,2,border_radius=7)
            label=self.font.render(text,True,(255,238,199))
            screen.blit(label,label.get_rect(center=rect.center))
        help_msg=self.font.render('滑鼠點選 / ↑↓ 選擇    Enter / E 購買    Esc 關閉商店',True,(206,211,232))
        screen.blit(help_msg,(panel.x+29,panel.bottom-23))
        if self.notice_timer>0:
            notice=self.font.render(self.notice,True,(255,220,133))
            screen.blit(notice,(panel.x+30,panel.bottom-115))
