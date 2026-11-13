"""Loads actual AI-generated four-direction PNG sprite sheets (4 frames x 4 rows)."""
from pathlib import Path
import pygame

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS={'down':0,'left':1,'right':2,'up':3}

class NPCSpriteLibrary:
    def __init__(self):
        self.cache={}
        self.scaled_cache={}
        self.reference_heights={}

    def frames(self,name):
        """Read each directional atlas once, keeping the 4x4 ordering.

        A few generated walk frames vary significantly in visible height.
        Normalize only frames outside a small tolerance at decode time;
        during rendering every frame uses the SAME character scale.
        """
        if name not in self.cache:
            path=ROOT/'assets/characters/npcs'/f'{name}.png'
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
            # Maintain a consistent body height while retaining minor natural
            # 1-3 pixel fluctuations. Correct both shrunken and enlarged art.
            for row in range(4):
                for col in range(4):
                    frame=atlas[row][col]
                    bounds=frame.get_bounding_rect(min_alpha=25)
                    if not bounds.height or abs(bounds.height-reference)<=max(2,reference*0.05):
                        continue
                    factor=reference/bounds.height
                    width=min(fw,max(1,round(bounds.width*factor)))
                    height=min(fh,max(1,round(bounds.height*factor)))
                    cropped=frame.subsurface(bounds).copy()
                    corrected=pygame.transform.scale(cropped,(width,height))
                    cell=pygame.Surface((fw,fh),pygame.SRCALPHA)
                    cell.blit(corrected,((fw-width)//2,max(0,fh-height-4)))
                    atlas[row][col]=cell
            self.cache[name]=atlas
            self.reference_heights[name]=reference
        return self.cache[name]

    def render(self,surface,name,direction,moving,frame,x,y,scale=1.0,pose='stand'):
        atlas=self.frames(name)
        row=DIRECTIONS.get(direction,0)
        col=(int(frame)%4) if moving or int(frame)>0 else 0
        sprite=atlas[row][col]
        visible=sprite.get_bounding_rect(min_alpha=25)
        if visible.w<=0 or visible.h<=0:
            return
        # A shared on-screen body height (not a shared model/hairstyle).
        # Separate idle/walk frames may have different invisible margins.
        target_h=71 if pose=='sit' else 80
        # Older merchant data can request 1.22x or 1.3x. Cap that historical
        # multiplier so NPCs never dwarf the player or other NPCs.
        adjustment=max(.95,min(1.07,float(scale)))
        factor=(target_h/max(1,self.reference_heights[name]))*adjustment
        key=(name,row,col,round(factor,4))
        if key not in self.scaled_cache:
            dim=(max(1,round(sprite.get_width()*factor)),
                 max(1,round(sprite.get_height()*factor)))
            self.scaled_cache[key]=pygame.transform.scale(sprite,dim)
        sprite=self.scaled_cache[key]
        visible=sprite.get_bounding_rect(min_alpha=25)
        surface.blit(sprite,(round(x-visible.centerx),round(y-visible.bottom)))
