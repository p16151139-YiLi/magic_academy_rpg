"""Shared feet-direction rules for keyboard and AI controlled characters."""
def facing_from_actual_displacement(dx, dy, previous='down', epsilon=0.001):
    if dx*dx + dy*dy <= epsilon*epsilon:
        return previous, False
    if abs(dx)>abs(dy):
        return ('right' if dx>0 else 'left'), True
    return ('down' if dy>0 else 'up'), True

def foot_rect_at(pygame_module, x, y, size):
    w, h = size
    return pygame_module.Rect(round(x-w/2),round(y-h/2),w,h)

def footprint_clear(pygame_module, x, y, size, obstacles, bounds=None):
    foot=foot_rect_at(pygame_module,x,y,size)
    if bounds is not None and not bounds.contains(foot):
        return False
    return not any(foot.colliderect(block) for block in obstacles)
