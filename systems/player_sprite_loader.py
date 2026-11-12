import json
from pathlib import Path

import pygame


class PlayerSpriteLoader:
    """載入職業精靈圖；未製作的職業暫用均衡型法師動畫。"""

    FALLBACK_CLASS = "balanced_mage"
    CLASS_TINTS = {
        "melee_mage": (255, 220, 205, 255),
        "ranged_mage": (205, 255, 230, 255),
    }

    def __init__(self, root=None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]
        config_path = self.root / "data/characters/animation_config.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.sprite_root = self.root / "assets/characters/sprites"

    def _sheet_path(self, class_id, state):
        requested = self.sprite_root / class_id / f"{state}.png"
        if requested.is_file():
            return requested, False

        fallback = self.sprite_root / self.FALLBACK_CLASS / f"{state}.png"
        if fallback.is_file():
            return fallback, class_id != self.FALLBACK_CLASS

        return None, False

    @staticmethod
    def _enhance_frame(frame):
        # 避免在含 alpha 的 Surface 上直接使用 BLEND_RGBA_ADD 改動透明通道。
        rgb = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        rgb.fill((17, 14, 21, 0))
        frame.blit(rgb, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return frame

    def load_into(self, animator):
        if pygame.display.get_surface() is None:
            raise RuntimeError("載入角色精靈圖前必須先建立 Pygame 顯示畫面")

        fw = int(self.config["frame_width"])
        fh = int(self.config["frame_height"])
        scale = int(self.config.get("display_scale", 1))
        directions = self.config["directions"]

        loaded, missing, fallbacks = [], [], []

        for state, count in self.config["states"].items():
            path, using_fallback = self._sheet_path(animator.class_id, state)

            if path is None:
                missing.append(state)
                continue

            sheet = pygame.image.load(str(path)).convert_alpha()
            expected = (fw * int(count), fh * len(directions))
            if sheet.get_size() != expected:
                raise ValueError(
                    f"{path.name} 尺寸為 {sheet.get_size()}，預期為 {expected}"
                )

            for row, direction in enumerate(directions):
                frames = []
                for column in range(int(count)):
                    area = pygame.Rect(column * fw, row * fh, fw, fh)
                    frame = sheet.subsurface(area).copy()

                    if scale != 1:
                        frame = pygame.transform.scale(
                            frame, (fw * scale, fh * scale)
                        )

                    # 不使用職業乘色濾鏡，避免法師變灰、偏綠。
                    # 只增亮不透明像素，透明背景維持原樣。
                    frame = self._enhance_frame(frame)

                    frames.append(frame)

                animator.register(state, direction, frames)

            loaded.append(state)
            if using_fallback:
                fallbacks.append(state)

        return {
            "class_id": animator.class_id,
            "loaded": loaded,
            "missing": missing,
            "fallback_class": self.FALLBACK_CLASS if fallbacks else None,
            "fallback_states": fallbacks,
        }
