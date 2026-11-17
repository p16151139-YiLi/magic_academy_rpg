"""Scene chair props: transparent sprites, independent solid footprints and seat anchors."""
from pathlib import Path
import pygame
from systems.chair_geometry import chair_walking_obstacles, chair_solid_rects

class ChairSystem:
    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}
        self.backrest_cache = {}

    def placements(self, map_data):
        return map_data.get("chairs", [])

    def rects(self, map_data):
        return [pygame.Rect(*box) for item in self.placements(map_data) for box in chair_walking_obstacles(item)]

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

    def front_backrest(self, chair):
        """Visible outside of the sitter: back-facing high-chair back panel.

        Uses alpha from the actual independent chair PNG, not a cutout of the
        environment or a cropped seated person. The upper part of a seated
        sprite (hair/head) stays visible above the high chair back. A seated
        NPC's knees/boots naturally disappear behind its own chair back.
        The physical chair colliders are unchanged by this visual pass.
        """
        if chair.get('facing') != 'up':
            return None
        picture = self.image(chair)
        key = (chair['image'], int(chair['width']), int(chair['height']),
               pygame.display.get_init() and pygame.display.get_surface() is not None)
        if key not in self.backrest_cache:
            occlusion = pygame.Surface(picture.get_size(), pygame.SRCALPHA)
            # The previous mask covered y=17..71 and hid almost the entire
            # seated torso.  Keep the upper backrest behind the actor; only
            # its lower rail and the two front leg strips pass in front of
            # the lower body.  Coordinates are measured on the 82x88 PNG.
            # This preserves the head, shoulders, arms and book-facing torso
            # while naturally hiding the knees/boots behind the chair.
            regions = (
                pygame.Rect(13, 48, 57, 10),   # lower front rail of backrest
                pygame.Rect(13, 58, 14, 30),   # left front leg
                pygame.Rect(55, 58, 15, 30),   # right front leg
            )
            for region in regions:
                occlusion.blit(picture, region.topleft, region)
            self.backrest_cache[key] = occlusion
        return self.backrest_cache[key]

    def seat_for(self, map_data, point, max_distance=62):
        chairs = self.placements(map_data)
        if not chairs:
            return None
        pt = pygame.Vector2(point)
        candidate = min(chairs, key=lambda item:pt.distance_squared_to(item["seat_anchor"]))
        if pt.distance_to(candidate["seat_anchor"]) <= max_distance:
            return candidate
        return None
