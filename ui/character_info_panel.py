
import json
from pathlib import Path
from systems.save_store import read_json

import pygame


ROOT = Path(__file__).resolve().parents[1]


class CharacterInfoPanel:

    def __init__(self):
        self.data_path = ROOT / "data/player/player_data.json"
        self.portrait_dir = ROOT / "assets/characters/portraits"

        self.portrait_files = {
            "balanced_mage": "balanced_mage_portrait.png",
            "melee_mage": "melee_mage_portrait.png",
            "ranged_mage": "ranged_mage_portrait.png",
        }

        self.portrait_cache = {}

        self.colors = {
            "background": (25, 30, 49),
            "panel": (37, 44, 67),
            "border": (113, 126, 159),
            "white": (239, 242, 250),
            "muted": (173, 186, 207),
            "gold": (244, 204, 111),
            "hp": (207, 88, 96),
            "mp": (93, 153, 230),
            "exp": (120, 200, 150),
        }

        font_path = ROOT / "assets/fonts/NotoSansTC-Regular.ttf"

        if font_path.exists():
            self.font = pygame.font.Font(str(font_path), 21)
            self.small_font = pygame.font.Font(str(font_path), 17)
            self.title_font = pygame.font.Font(str(font_path), 28)
        else:
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 20)
            self.title_font = pygame.font.Font(None, 32)

    def load_data(self):
        return read_json(self.data_path, {})

    def get_attribute(self, data, key, default=0):
        attributes = data.get("attributes", {})

        if isinstance(attributes, dict) and key in attributes:
            return attributes[key]

        return data.get(key, default)

    def get_portrait(self, class_id, size=(175, 175)):
        filename = self.portrait_files.get(class_id)

        if filename is None:
            return None

        cache_key = (class_id, size)

        if cache_key in self.portrait_cache:
            return self.portrait_cache[cache_key]

        path = self.portrait_dir / filename

        if not path.exists():
            return None

        try:
            image = pygame.image.load(str(path)).convert_alpha()
            image = pygame.transform.scale(image, size)
        except (pygame.error, OSError, ValueError) as exc:
            print(f"角色肖像載入失敗 {path}: {type(exc).__name__}: {exc}")
            return None

        self.portrait_cache[cache_key] = image

        return image

    def text(self, surface, value, x, y, color=None, font=None):
        color = color or self.colors["white"]
        font = font or self.font

        image = font.render(str(value), True, color)
        surface.blit(image, (int(x), int(y)))

    def bar(
        self, surface, x, y, width, height,
        current, maximum, color
    ):
        try:
            maximum = max(1, float(maximum))
            ratio = max(0, min(1, float(current) / maximum))
        except (ValueError, TypeError):
            ratio = 0

        background = pygame.Rect(x, y, width, height)

        pygame.draw.rect(
            surface, (17, 21, 36), background
        )

        fill_width = int(width * ratio)

        if fill_width > 0:
            pygame.draw.rect(
                surface,
                color,
                (x, y, fill_width, height)
            )

        pygame.draw.rect(
            surface,
            self.colors["border"],
            background,
            1
        )

    def draw(self, surface, rect):
        data = self.load_data()

        if not isinstance(rect, pygame.Rect):
            rect = pygame.Rect(rect)

        # 使用獨立透明圖層，避免畫出面板範圍
        panel = pygame.Surface(
            (rect.width, rect.height),
            pygame.SRCALPHA
        )

        pygame.draw.rect(
            panel,
            self.colors["background"],
            panel.get_rect(),
            border_radius=8
        )

        pygame.draw.rect(
            panel,
            self.colors["border"],
            panel.get_rect(),
            2,
            border_radius=8
        )

        name = data.get("name", "見習冒險者")
        class_id = data.get("class_id", "balanced_mage")
        class_name = data.get("class_name", "均衡型法師")

        level = data.get("level", 1)
        gold = data.get("gold", 0)

        hp = data.get("hp", 100)
        max_hp = data.get("max_hp", 100)

        mp = data.get("mp", 50)
        max_mp = data.get("max_mp", 50)

        exp = data.get("exp", 0)
        exp_max = data.get("exp_to_next_level", 100)

        # 左側：角色立繪
        portrait = self.get_portrait(class_id)

        portrait_box = pygame.Rect(24, 45, 196, 196)

        pygame.draw.rect(
            panel,
            self.colors["panel"],
            portrait_box,
            border_radius=6
        )

        if portrait is not None:
            panel.blit(
                portrait,
                portrait.get_rect(
                    center=portrait_box.center
                )
            )

        # 右側：角色基本資料
        self.text(
            panel, name, 245, 32,
            self.colors["gold"],
            self.title_font
        )

        self.text(
            panel,
            f"Lv. {level}  {class_name}",
            245, 77,
            self.colors["muted"]
        )

        self.text(
            panel,
            f"HP  {hp} / {max_hp}",
            245, 117,
            font=self.small_font
        )

        self.bar(
            panel, 245, 146, 360, 13,
            hp, max_hp,
            self.colors["hp"]
        )

        self.text(
            panel,
            f"MP  {mp} / {max_mp}",
            245, 174,
            font=self.small_font
        )

        self.bar(
            panel, 245, 203, 360, 13,
            mp, max_mp,
            self.colors["mp"]
        )

        self.text(
            panel,
            f"EXP  {exp} / {exp_max}",
            245, 235,
            font=self.small_font
        )

        self.bar(
            panel, 245, 264, 360, 11,
            exp, exp_max,
            self.colors["exp"]
        )

        # 下方：戰鬥能力
        pygame.draw.line(
            panel,
            self.colors["border"],
            (25, 302),
            (rect.width - 25, 302),
            1
        )

        stats = [
            ("攻擊", "attack"),
            ("防禦", "defense"),
            ("魔力", "magic"),
            ("智力", "intelligence"),
            ("敏捷", "agility"),
            ("體力", "vitality"),
            ("幸運", "luck"),
        ]

        for i, (label, key) in enumerate(stats):
            col = i % 4
            row = i // 4

            x = 35 + col * 205
            y = 325 + row * 43

            value = self.get_attribute(data, key)

            self.text(
                panel,
                f"{label}：{value}",
                x, y,
                font=self.small_font
            )

        self.text(
            panel,
            f"金幣：{gold}",
            35, 425,
            self.colors["gold"]
        )

        surface.blit(panel, rect.topleft)
