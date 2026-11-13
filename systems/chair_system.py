"""Scene chair props: transparent sprites, independent solid footprints and seat anchors."""
from pathlib import Path
import pygame

class ChairSystem:
    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}

    def placements(self, map_data):
        return map_data.get("chairs", [])

    def rects(self, map_data):
        return [pygame.Rect(*item["collision_rect"]) for item in self.placements(map_data)]

    def image(self, chair):
        """Load transparent chair PNG with or without an initialized display.

        convert_alpha() is only valid when a display mode exists.  The raw
        PNG Surface already retains its per-pixel alpha for image auditing;
        once a real display is initialized we create/cache a converted copy
        for fast game rendering.  This never changes collisions or seating.
        """
        size = (int(chair["width"]), int(chair["height"]))
        display_ready = (pygame.display.get_init()
                         and pygame.display.get_surface() is not None)
        key = (chair["image"], *size, display_ready)
        if key not in self.cache:
            path = self.root / chair["image"]
            img = pygame.image.load(str(path))
            if display_ready:
                img = img.convert_alpha()
            if img.get_size() != size:
                img = pygame.transform.scale(img, size)
            self.cache[key] = img
        return self.cache[key]

    def seat_for(self, map_data, point, max_distance=62):
        chairs = self.placements(map_data)
        if not chairs:
            return None
        pt = pygame.Vector2(point)
        candidate = min(chairs, key=lambda item:pt.distance_squared_to(item["seat_anchor"]))
        if pt.distance_to(candidate["seat_anchor"]) <= max_distance:
            return candidate
        return None
