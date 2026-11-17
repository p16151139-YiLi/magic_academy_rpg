"""Pixel-aligned directional chair geometry, measured from actual transparent PNGs.

Physical chair-leg colliders are small independent rectangles.  The cushion
is a separately reserved seat area, never a third physical leg.  Ordinary
walking actors respect the reservation, while the designated stationary
occupant uses the seat anchor and does not run walk collision against itself.
"""

def chair_solid_rects(chair):
    parts=chair.get('collision_rects')
    if parts is not None:
        if len(parts)!=2 or not all(len(part)==4 for part in parts):
            raise ValueError('椅子必須提供兩個獨立椅腳碰撞矩形：'+str(chair.get('id')))
        return [list(p) for p in parts]
    return [list(chair['collision_rect'])] if 'collision_rect' in chair else []

def chair_seat_reservation(chair):
    """Access-controlled cushion footprint: excludes the named seated actor."""
    seat=chair.get('seat_block_rect')
    return list(seat) if seat else None

def chair_walking_obstacles(chair):
    """Solid obstacles for player and non-occupant walking NPCs."""
    parts=chair_solid_rects(chair)
    cushion=chair_seat_reservation(chair)
    return parts+([cushion] if cushion else [])

def seat_at(chair):
    return tuple(chair['seat_anchor'])
