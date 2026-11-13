
from pathlib import Path
import pygame


class MapRenderer:
    """根據地圖 JSON 載入與繪製圖層。"""

    def __init__(self, root_path):
        self.root = Path(root_path)
        self.map_data = None
        self.ground = None
        self.objects = None
        self.foreground = None
        self.occluders = []
        self.decals = []

    def _load_image(self, relative_path, required=True):
        if not relative_path:
            if required:
                raise ValueError("缺少必要的地圖圖片路徑")
            return None

        path = self.root / relative_path

        if not path.is_file():
            if required:
                raise FileNotFoundError(
                    f"找不到地圖圖片：{path}"
                )
            return None

        return pygame.image.load(str(path)).convert_alpha()

    def _fallback_ground(self, map_data):
        """Draw a usable floor if an optional map background is unavailable."""
        width, height = map_data["width"], map_data["height"]
        ground = pygame.Surface((width, height)).convert()
        ground.fill((43, 48, 69))
        tile = 64
        for yy in range(0, height, tile):
            for xx in range(0, width, tile):
                color = (53, 58, 79) if (xx // tile + yy // tile) % 2 else (43, 48, 69)
                pygame.draw.rect(ground, color, (xx, yy, tile, tile))
        pygame.draw.rect(ground, (156, 133, 92), ground.get_rect(), 12)
        return ground

    def begin_load(self, map_data):
        """Schedule map assets for frame-by-frame loading in WebAssembly.

        This is intentionally separate from load(): tests and tools calling
        load() still receive a fully-loaded synchronous map, as before.
        """
        if not pygame.display.get_surface():
            raise RuntimeError("請先使用 pygame.display.set_mode() 建立畫面")
        layers = map_data.get("layers", {})
        tasks = [
            ("ground", layers.get("ground", map_data.get("background")), None),
            ("objects", layers.get("objects"), None),
            ("foreground", layers.get("foreground"), None),
        ]
        for item in map_data.get("occluders", []):
            tasks.append(("occluder", item.get("image"), item))
        for item in map_data.get("decals", []):
            tasks.append(("decal", item.get("image"), item))
        self._load_pending = tasks
        self._load_count = len(tasks)
        self._load_target = map_data
        self._load_parts = {"ground": None, "objects": None,
                            "foreground": None, "occluders": [], "decals": []}
        self.load_warnings = []
        self.loading = True

    @property
    def load_progress(self):
        if not getattr(self, "loading", False):
            return 1.0
        return 1.0 - len(self._load_pending) / max(1, self._load_count)

    def step_load(self):
        """Decode at most one image per frame, so the browser stays responsive."""
        if not getattr(self, "loading", False):
            return True
        if self._load_pending:
            kind, relative, item = self._load_pending.pop(0)
            try:
                image = self._load_image(relative, required=False)
                if kind in ("ground", "objects", "foreground") and image is not None:
                    expected = (self._load_target["width"], self._load_target["height"])
                    if image.get_size() != expected:
                        raise ValueError(f"{kind} 尺寸錯誤：{image.get_size()} != {expected}")
            except (OSError, RuntimeError, ValueError, pygame.error) as exc:
                image = None
                msg = f"地圖素材略過 {relative}: {exc}"
                self.load_warnings.append(msg)
                print(msg)
            if kind in ("ground", "objects", "foreground"):
                self._load_parts[kind] = image
            elif image is not None and kind == "occluder":
                self._load_parts["occluders"].append(
                    (int(item["depth_y"]), image, int(item["x"]), int(item["y"]),
                     bool(item.get("fade_when_overlapping", True))))
            elif image is not None and kind == "decal":
                self._load_parts["decals"].append(
                    (image, int(item["x"]), int(item["y"]),
                     bool(item.get("fade_when_overlapping", True))))
        if self._load_pending:
            return False
        parts = self._load_parts
        if parts["ground"] is None:
            parts["ground"] = self._fallback_ground(self._load_target)
        self.map_data = self._load_target
        self.ground = parts["ground"]
        self.objects = parts["objects"]
        self.foreground = parts["foreground"]
        self.occluders = parts["occluders"]
        self.decals = parts["decals"]
        self.loading = False
        self._load_parts = None
        return True

    def load(self, map_data):
        """Existing synchronous API, retained for tooling and older tests."""
        self.begin_load(map_data)
        while not self.step_load():
            pass

    def _draw_layer(self, screen, image, camera):
        if image is None:
            return

        # 只擷取目前攝影機可見的區域
        source = pygame.Rect(
            int(camera.x),
            int(camera.y),
            screen.get_width(),
            screen.get_height()
        )

        source = source.clip(image.get_rect())

        if source.width > 0 and source.height > 0:
            screen.blit(
                image,
                (source.x - camera.x, source.y - camera.y),
                source
            )

    def draw_ground(self, screen, camera):
        self._draw_layer(screen, self.ground, camera)

    def draw_objects(self, screen, camera):
        self._draw_layer(screen, self.objects, camera)

    def draw_decals(self, screen, camera):
        # Non-interactive world art is below actors; occluder pass above actors
        # runs according to each sprite's feet depth, never globally on top.
        for decal in self.decals:
            # V9.4.2 streamed decals store (sprite, x, y, fade_flag).
            # Older callers use (sprite, x, y). Both layouts must render.
            # The optional flag is metadata; decals remain under actors.
            sprite, x, y = decal[:3]
            screen.blit(sprite, (round(x-camera.x), round(y-camera.y)))

    def draw_foreground(self, screen, camera):
        self._draw_layer(screen, self.foreground, camera)

    def draw(self, screen, camera):
        """目前無角色時，依序繪製三個圖層。"""
        self.draw_ground(screen, camera)
        self.draw_objects(screen, camera)
        self.draw_foreground(screen, camera)
