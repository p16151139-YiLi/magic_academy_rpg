
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

    def load(self, map_data):
        """載入 MapManager 提供的地圖資料。"""

        if not pygame.display.get_surface():
            raise RuntimeError(
                "請先使用 pygame.display.set_mode() 建立畫面"
            )

        layers = map_data.get("layers", {})

        ground_path = layers.get(
            "ground", map_data.get("background")
        )

        # 先載入到暫存變數，避免失敗時破壞原本地圖
        # 尚未提供室內背景時，使用清楚標示的暫時地板，避免場景切換崩潰。
        ground = self._load_image(ground_path, required=False)
        if ground is None:
            width, height = map_data["width"], map_data["height"]
            ground = pygame.Surface((width, height)).convert()
            ground.fill((43, 48, 69))
            tile = 64
            for yy in range(0, height, tile):
                for xx in range(0, width, tile):
                    color = (53, 58, 79) if (xx // tile + yy // tile) % 2 else (43, 48, 69)
                    pygame.draw.rect(ground, color, (xx, yy, tile, tile))
            pygame.draw.rect(ground, (156, 133, 92), ground.get_rect(), 12)
        objects = self._load_image(
            layers.get("objects"), required=False
        )
        foreground = self._load_image(
            layers.get("foreground"), required=False
        )

        expected_size = (
            map_data["width"],
            map_data["height"]
        )

        for name, image in [
            ("ground", ground),
            ("objects", objects),
            ("foreground", foreground)
        ]:
            if image is not None and image.get_size() != expected_size:
                raise ValueError(
                    f"{name} 圖層尺寸不符合地圖設定："
                    f"{image.get_size()} != {expected_size}"
                )

        self.map_data = map_data
        self.ground = ground
        self.objects = objects
        self.foreground = foreground
        self.occluders = []
        for item in map_data.get('occluders', []):
            asset = self._load_image(item.get('image'), required=False)
            if asset is not None:
                self.occluders.append((int(item['depth_y']), asset,
                                       int(item['x']), int(item['y']), bool(item.get('fade_when_overlapping', True))))
        self.decals = []
        for item in map_data.get('decals', []):
            asset = self._load_image(item.get('image'), required=False)
            if asset is not None:
                self.decals.append((asset, int(item['x']), int(item['y']), bool(item.get('fade_when_overlapping', True))))

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
        for sprite, x, y in self.decals:
            screen.blit(sprite, (round(x-camera.x), round(y-camera.y)))

    def draw_foreground(self, screen, camera):
        self._draw_layer(screen, self.foreground, camera)

    def draw(self, screen, camera):
        """目前無角色時，依序繪製三個圖層。"""
        self.draw_ground(screen, camera)
        self.draw_objects(screen, camera)
        self.draw_foreground(screen, camera)
