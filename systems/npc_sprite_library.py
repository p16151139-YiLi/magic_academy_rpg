"""Loads actual AI-generated four-direction PNG sprite sheets (4 frames x 4 rows)."""
from pathlib import Path
import pygame

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS={'down':0,'left':1,'right':2,'up':3}

class NPCSpriteLibrary:
    def __init__(self):
        self.cache={}
        self.scaled_cache={}

    def frames(self,name):
        if name not in self.cache:
            path=ROOT/'assets/characters/npcs'/f'{name}.png'
            if not path.is_file():
                raise FileNotFoundError('NPC 專屬圖片遺失: '+str(path))
            sprite=pygame.image.load(str(path)).convert_alpha()
            if sprite.get_width()%4 or sprite.get_height()%4:
                raise ValueError('NPC 圖集必須是 4×4: '+str(path))
            fw=sprite.get_width()//4;fh=sprite.get_height()//4
            self.cache[name]=[[sprite.subsurface((col*fw,row*fh,fw,fh)).copy() for col in range(4)] for row in range(4)]
        return self.cache[name]

    def render(self,surface,name,direction,moving,frame,x,y,scale=1.0):
        atlas=self.frames(name)
        row=DIRECTIONS.get(direction,0)
        col=frame % 4  # supports dedicated four-frame seated idle/talking cycles
        sprite=atlas[row][col]
        if scale != 1.0:
            scale=max(0.65,min(1.5,float(scale)))
            key=(name,row,col,scale)
            if key not in self.scaled_cache:
                sz=(max(1,round(sprite.get_width()*scale)),
                    max(1,round(sprite.get_height()*scale)))
                # Pixel-perfect nearest-neighbour scaling, cached once per frame.
                self.scaled_cache[key]=pygame.transform.scale(sprite,sz)
            sprite=self.scaled_cache[key]
        # IMPORTANT: the transparent border differs between AI sprites and
        # frames. Using sprite.get_rect(midbottom=...) makes seated actors float
        # or cuts their shoes. Anchor the *visible alpha pixels* to the floor.
        visible=sprite.get_bounding_rect(min_alpha=25)
        if visible.w and visible.h:
            left=round(x-visible.centerx)
            top=round(y-visible.bottom)
            surface.blit(sprite,(left,top))
