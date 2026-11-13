from ui.character_portrait import CharacterPortraitManager

import json
import pygame
from pathlib import Path
from systems.save_store import read_json

ROOT = Path(__file__).resolve().parents[1]


class CharacterPanel:

    def __init__(self):
        self.data_path = ROOT / "data/player/player_data.json"
        self.portrait_manager = CharacterPortraitManager()

    def load_data(self):
        return read_json(self.data_path, {})

    def draw(self, screen, font, rect):
        data = self.load_data()

        # 讀取玩家職業
        job_id = data.get("class_id", "balanced_mage")

        # 在角色資訊介面顯示對應立繪
        self.portrait_manager.draw(
            screen,
            job_id,
            rect[0] + 570,
            rect[1] + 65,
            (175, 175)
        )

        x, y, w, h = rect

        def text(value, px, py, size=22, color=(235, 226, 205)):
            f = font(size)
            image = f.render(str(value), True, color)
            screen.blit(image, (int(px), int(py)))

        def bar(px, py, width, value, maximum, color):
            pygame.draw.rect(
                screen, (65, 60, 75),
                (px, py, width, 18)
            )

            ratio = max(0, min(1, value / max(1, maximum)))

            pygame.draw.rect(
                screen, color,
                (px, py, int(width * ratio), 18)
            )

            pygame.draw.rect(
                screen, (190, 170, 135),
                (px, py, width, 18), 2
            )

        text(data["name"], x + 30, y + 20, 26,
             (245, 210, 145))

        text(f'Lv. {data["level"]}', x + 30, y + 65, 21)

        text("HP", x + 30, y + 110, 20)
        bar(
            x + 95, y + 115, 250,
            data["hp"], data["max_hp"],
            (205, 75, 85)
        )

        text(
            f'{data["hp"]}/{data["max_hp"]}',
            x + 365, y + 108, 18
        )

        text("MP", x + 30, y + 150, 20)
        bar(
            x + 95, y + 155, 250,
            data["mp"], data["max_mp"],
            (75, 145, 225)
        )

        text(
            f'{data["mp"]}/{data["max_mp"]}',
            x + 365, y + 148, 18
        )

        names = {
            "attack": "攻擊力",
            "defense": "防禦力",
            "magic": "魔法力",
            "intelligence": "智力",
            "agility": "敏捷",
            "vitality": "體力",
            "luck": "幸運"
        }

        for i, (key, name) in enumerate(names.items()):
            column = i // 4
            row = i % 4

            px = x + 30 + column * 280
            py = y + 200 + row * 31

            text(
                f'{name}：{data["attributes"].get(key, 0)}',
                px, py, 18
            )

        text(
            f'金幣：{data["gold"]}',
            x + 650, y + 25, 19,
            (245, 210, 125)
        )
