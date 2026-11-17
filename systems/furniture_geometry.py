"""Single source of truth for segmented colliders of independent furniture sprites.

Geometry has no dependency on pygame, so visual/route regression works even if SDL
cannot be installed. Each collision rectangle is local to an independently drawn PNG.
"""

def furniture_world_rects(item):
    x,y,w,h = (int(item[k]) for k in ('x','y','width','height'))
    parts=item.get('collision_rects',[])
    if not isinstance(parts,list):
        raise ValueError('家具 collision_rects 必須為清單：'+str(item.get('id')))
    result=[]
    for p in parts:
        if len(p)!=4 or not all(type(a) is int for a in p):
            raise ValueError('家具碰撞必須是四個整數：'+str(item.get('id')))
        a,b,pw,ph=p
        if a<0 or b<0 or pw<=0 or ph<=0 or a+pw>w or b+ph>h:
            raise ValueError('家具碰撞必須在物件實際圖框內：'+str(item.get('id')))
        result.append([x+a,y+b,pw,ph])
    return result

def map_furniture_world_rects(map_data):
    return [r for item in map_data.get('furniture',[]) for r in furniture_world_rects(item)]


def within_map(map_data,item):
    return (0<=item['x'] and 0<=item['y'] and item['x']+item['width']<=map_data['width']
            and item['y']+item['height']<=map_data['height'])
