"""Loads audited NPC direction atlases and dedicated seated sprites."""
from pathlib import Path
import json
import pygame

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS={'down':0,'left':1,'right':2,'up':3}
DIRECTION_ORDER=('down','left','right','up')
MANIFEST_PATH=ROOT/'data/npcs/sprite_direction_manifest.json'
with MANIFEST_PATH.open('r',encoding='utf-8') as f:
    DIRECTION_MANIFEST=json.load(f)
SEATED_ASSETS={name:entry.get('seated_assets',{})
               for name,entry in DIRECTION_MANIFEST['sprites'].items()
               if entry.get('seated_assets')}
SEATED_ONLY_SPRITES={name for name,entry in DIRECTION_MANIFEST['sprites'].items()
                     if entry.get('mode')=='seated_only'}
TARGET_VISIBLE_HEIGHT=94

class NPCSpriteLibrary:
    def __init__(self):
        self.cache={}
        self.scaled_cache={}
        self.reference_heights={}
        self.seated_cache={}

    def frames(self,name):
        """Decode a validated 4x4 atlas: rows down, left, right, up."""
        entry=DIRECTION_MANIFEST['sprites'].get(name)
        if entry is None:
            raise KeyError(f'NPC 方向清單沒有角色：{name}')
        if entry.get('mode')!='four_direction_atlas':
            raise ValueError(f'{name} 是固定坐姿角色，禁止使用未校正的站立方向圖集')
        if tuple(entry.get('row_order',()))!=DIRECTION_ORDER:
            raise ValueError(f'{name} 的方向列序與遊戲方向列序不一致')
        if name not in self.cache:
            path=ROOT/entry['atlas']
            if not path.is_file():
                raise FileNotFoundError('NPC 專屬圖片遺失: '+str(path))
            sprite=pygame.image.load(str(path)).convert_alpha()
            if sprite.get_width()%4 or sprite.get_height()%4:
                raise ValueError('NPC 圖集必須是 4×4: '+str(path))
            fw=sprite.get_width()//4
            fh=sprite.get_height()//4
            atlas=[[sprite.subsurface((col*fw,row*fh,fw,fh)).copy()
                    for col in range(4)] for row in range(4)]
            heights=sorted(frame.get_bounding_rect(min_alpha=25).height
                           for row in atlas for frame in row)
            reference=max(1,heights[len(heights)//2])
            # Normalize visible height only; preserve each frame's aspect ratio.
            for row in range(4):
                for col in range(4):
                    frame=atlas[row][col]
                    bounds=frame.get_bounding_rect(min_alpha=25)
                    if not bounds.height or bounds.height==reference:
                        continue
                    factor=reference/bounds.height
                    width=max(1,round(bounds.width*factor))
                    height=max(1,round(bounds.height*factor))
                    cropped=frame.subsurface(bounds).copy()
                    corrected=pygame.transform.scale(cropped,(width,height))
                    cell=pygame.Surface((fw,fh),pygame.SRCALPHA)
                    cell.blit(corrected,((fw-width)//2,max(0,fh-height-4)))
                    atlas[row][col]=cell
            self.cache[name]=atlas
            self.reference_heights[name]=reference
        return self.cache[name]

    def preload(self,name,pose='stand',direction='down'):
        """Warm the correct asset for an NPC's active pose.

        A seated-only character (for example Selena) has no valid standing
        atlas.  Its dedicated seated PNG must be loaded through the seated
        asset path instead of calling frames(), which intentionally rejects
        legacy front-only atlases.
        """
        if pose == 'sit':
            return self._seated_sprite(name,direction)
        if pose in ('stand', 'roam'):
            return self.frames(name)
        raise ValueError(f'{name} 的 NPC 姿勢不受支援：{pose}')

    def _seated_sprite(self,name,direction):
        assets=SEATED_ASSETS.get(name,{})
        filename=assets.get(direction)
        if not filename:
            allowed=', '.join(assets) or 'none'
            raise ValueError(f'{name} 尚未製作 {direction} 坐姿模型；目前只允許：{allowed}')
        path=ROOT/filename
        if not path.is_file():
            raise FileNotFoundError('NPC 坐姿素材遺失: '+str(path))
        key=(name,direction,filename)
        if key not in self.seated_cache:
            raw=pygame.image.load(str(path)).convert_alpha()
            visible=raw.get_bounding_rect(min_alpha=25)
            if visible.height<=0:
                raise ValueError('坐姿模型是空白圖片：'+str(path))
            cropped=raw.subsurface(visible).copy()
            # Preserve original width/height ratio. Never widen a narrow model to
            # an arbitrary minimum, which previously distorted limbs and shoes.
            target_h=TARGET_VISIBLE_HEIGHT
            target_w=max(1,round(visible.width*target_h/visible.height))
            self.seated_cache[key]=pygame.transform.scale(cropped,(target_w,target_h))
        return self.seated_cache[key]

    def render(self,surface,name,direction,moving,frame,x,y,scale=1.0,pose='stand'):
        if pose=='sit':
            if moving:
                raise ValueError('坐姿 NPC 不可播放行走動畫')
            sprite=self._seated_sprite(name,direction)
            surface.blit(sprite,(round(x-sprite.get_width()/2),round(y-sprite.get_height())))
            return
        atlas=self.frames(name)
        row=DIRECTIONS.get(direction)
        if row is None:
            raise ValueError(f'未知 NPC 面向方向：{direction}')
        col=(int(frame)%4) if moving or int(frame)>0 else 0
        sprite=atlas[row][col]
        visible=sprite.get_bounding_rect(min_alpha=25)
        if visible.w<=0 or visible.h<=0:
            return
        factor=TARGET_VISIBLE_HEIGHT/max(1,self.reference_heights[name])
        key=(name,row,col,round(factor,4))
        if key not in self.scaled_cache:
            dim=(max(1,round(sprite.get_width()*factor)),
                 max(1,round(sprite.get_height()*factor)))
            self.scaled_cache[key]=pygame.transform.scale(sprite,dim)
        sprite=self.scaled_cache[key]
        visible=sprite.get_bounding_rect(min_alpha=25)
        surface.blit(sprite,(round(x-visible.centerx),round(y-visible.bottom)))
