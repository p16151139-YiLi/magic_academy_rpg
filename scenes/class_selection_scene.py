
import pygame
from pathlib import Path

from scenes.scene_base import BaseScene
from systems.class_selection_bridge import ClassSelectionBridge


class ClassSelectionScene(BaseScene):

    CLASS_IDS = [
        "balanced_mage",
        "melee_mage",
        "ranged_mage",
    ]

    PORTRAIT_FILES = [
        "balanced_mage_portrait.png",
        "melee_mage_portrait.png",
        "ranged_mage_portrait.png",
    ]

    def __init__(self, ctx):
        super().__init__(ctx)

        self.class_bridge = ClassSelectionBridge()

        self.cards = [
            pygame.Rect(55, 165, 365, 440),
            pygame.Rect(457, 165, 365, 440),
            pygame.Rect(859, 165, 365, 440),
        ]

        self.back_button = pygame.Rect(35, 28, 145, 48)
        self.confirm_button = pygame.Rect(470, 632, 340, 58)

        self.gold = (235, 190, 95)
        self.bright_gold = (255, 225, 110)
        self.white = (245, 240, 255)
        self.gray = (170, 180, 205)

        self.themes = [
            {
                "background": (30, 39, 75),
                "accent": (115, 155, 245),
            },
            {
                "background": (72, 38, 48),
                "accent": (235, 145, 105),
            },
            {
                "background": (29, 65, 64),
                "accent": (125, 215, 180),
            },
        ]

        root = Path(__file__).resolve().parents[1]
        portrait_dir = root / "assets/characters/portraits"

        self.portraits = []

        for filename in self.PORTRAIT_FILES:
            image_path = portrait_dir / filename

            if image_path.exists():
                image = pygame.image.load(
                    str(image_path)
                ).convert_alpha()

                # 保留像素風格
                image = pygame.transform.scale(
                    image, (154, 154)
                )
            else:
                image = None

            self.portraits.append(image)

    def draw_background(self):
        screen = self.ctx.screen

        screen.fill((15, 13, 35))

        pygame.draw.circle(
            screen,
            (35, 30, 70),
            (640, 360),
            350
        )

        pygame.draw.circle(
            screen,
            (76, 61, 115),
            (640, 360),
            335,
            2
        )

        pygame.draw.line(
            screen,
            self.gold,
            (370, 138),
            (910, 138),
            2
        )

    def draw_button(self, rect, label, mouse):
        hovered = rect.collidepoint(mouse)

        background = (
            (100, 78, 40)
            if hovered
            else (43, 36, 77)
        )

        border = (
            self.bright_gold
            if hovered
            else self.gold
        )

        pygame.draw.rect(
            self.ctx.screen,
            background,
            rect,
            border_radius=8
        )

        pygame.draw.rect(
            self.ctx.screen,
            border,
            rect,
            2,
            border_radius=8
        )

        self.ctx.draw_text(
            label,
            self.ctx.font_medium,
            self.bright_gold if hovered else self.white,
            rect.centerx,
            rect.centery
        )

    def draw_wrapped_text(
        self, text, font, color,
        center_x, start_y, max_width,
        max_lines=2, line_height=23
    ):
        lines = []
        current = ""

        for char in str(text):
            trial = current + char

            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = char

        if current:
            lines.append(current)

        for index, line in enumerate(lines[:max_lines]):
            self.ctx.draw_text(
                line,
                font,
                color,
                center_x,
                start_y + index * line_height
            )

    def draw_card(self, index, info, mouse):
        screen = self.ctx.screen
        ctx = self.ctx

        rect = self.cards[index]
        theme = self.themes[index]

        selected = index == ctx.selected_class
        hovered = rect.collidepoint(mouse)

        background = theme["background"]

        if hovered:
            background = tuple(
                min(255, c + 15)
                for c in background
            )

        # 卡片陰影
        pygame.draw.rect(
            screen,
            (7, 7, 20),
            rect.move(5, 6),
            border_radius=10
        )

        # 卡片底色
        pygame.draw.rect(
            screen,
            background,
            rect,
            border_radius=10
        )

        border = (
            self.bright_gold if hovered
            else self.gold if selected
            else theme["accent"]
        )

        pygame.draw.rect(
            screen,
            border,
            rect,
            3 if hovered or selected else 2,
            border_radius=10
        )

        cx = rect.centerx
        top = rect.top

        # 職業名稱
        ctx.draw_text(
            info["name"],
            ctx.font_medium,
            self.bright_gold if selected or hovered
            else self.white,
            cx,
            top + 34
        )

        # 英文副標題
        ctx.draw_text(
            info.get("subtitle", ""),
            ctx.font_small,
            theme["accent"],
            cx,
            top + 65
        )

        # 立繪專用區域
        portrait_box = pygame.Rect(
            rect.left + 82,
            top + 83,
            200,
            158
        )

        pygame.draw.rect(
            screen,
            (20, 23, 45),
            portrait_box,
            border_radius=6
        )

        pygame.draw.rect(
            screen,
            theme["accent"],
            portrait_box,
            1,
            border_radius=6
        )

        portrait = self.portraits[index]

        if portrait is not None:
            portrait_rect = portrait.get_rect(
                center=portrait_box.center
            )
            screen.blit(portrait, portrait_rect)
        else:
            ctx.draw_text(
                "角色立繪",
                ctx.font_small,
                self.gray,
                portrait_box.centerx,
                portrait_box.centery
            )

        # 分隔線
        pygame.draw.line(
            screen,
            theme["accent"],
            (rect.left + 25, top + 251),
            (rect.right - 25, top + 251),
            1
        )

        # 職業介紹
        self.draw_wrapped_text(
            info.get("description", ""),
            ctx.font_small,
            self.white,
            cx,
            top + 274,
            rect.width - 35,
            max_lines=2
        )

        # 戰鬥特色
        ctx.draw_text(
            "戰鬥風格：" + info.get("combat_style", ""),
            ctx.font_small,
            self.bright_gold,
            cx,
            top + 327
        )

        # 能力值區域
        stats = info.get("stats", {})

        pygame.draw.line(
            screen,
            theme["accent"],
            (rect.left + 25, top + 353),
            (rect.right - 25, top + 353),
            1
        )

        ctx.draw_text(
            f"HP {stats.get('hp', 0)}"
            f"    MP {stats.get('mp', 0)}",
            ctx.font_small,
            (185, 235, 200),
            cx,
            top + 378
        )

        ctx.draw_text(
            f"ATK {stats.get('attack', 0)}"
            f"    DEF {stats.get('defense', 0)}",
            ctx.font_small,
            (185, 235, 200),
            cx,
            top + 408
        )

        if selected:
            pygame.draw.circle(
                screen,
                self.bright_gold,
                (rect.right - 23, rect.top + 23),
                10
            )

            pygame.draw.circle(
                screen,
                (45, 35, 70),
                (rect.right - 23, rect.top + 23),
                4
            )

    def draw(self):
        ctx = self.ctx
        mouse = pygame.mouse.get_pos()

        self.draw_background()

        ctx.draw_text(
            "選擇你的魔法職業",
            ctx.font_large,
            self.bright_gold,
            640,
            60
        )

        ctx.draw_text(
            "Choose Your Class",
            ctx.font_small,
            self.gray,
            640,
            108
        )

        self.draw_button(
            self.back_button,
            "返回",
            mouse
        )

        for index, info in enumerate(ctx.classes[:3]):
            self.draw_card(index, info, mouse)

        self.draw_button(
            self.confirm_button,
            "確認職業",
            mouse
        )

    def handle_event(self, event):

        if (
            event.type != pygame.MOUSEBUTTONDOWN
            or event.button != 1
        ):
            return None

        if self.back_button.collidepoint(event.pos):
            return "title"

        for index, rect in enumerate(self.cards):
            if rect.collidepoint(event.pos):
                self.ctx.selected_class = index
                return None

        if self.confirm_button.collidepoint(event.pos):
            selected_index = self.ctx.selected_class

            if not 0 <= selected_index < 3:
                return None

            selected_id = self.CLASS_IDS[selected_index]

            # 正式套用職業資料
            try:
                player_data = self.class_bridge.select_class(
                    selected_id
                )

            except Exception as error:
                print("職業選擇失敗：", repr(error))
                return None

            # 保留原本的職業資料
            self.ctx.selected_character_class = (
                self.ctx.classes[selected_index]
            )

            self.ctx.selected_class_id = selected_id

            print(
                "職業選擇完成：",
                player_data["class_name"]
            )

            return "game"

        return None
