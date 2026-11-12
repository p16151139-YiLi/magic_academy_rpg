import pygame
from scenes.scene_base import BaseScene


class TitleScene(BaseScene):

    def __init__(self, ctx):
        super().__init__(ctx)

        # 依照 1280 × 720 畫面校準
        self.buttons = {
            "start": pygame.Rect(158, 348, 275, 64),
            "settings": pygame.Rect(170, 424, 254, 54),
            "credits": pygame.Rect(170, 487, 254, 54),
            "quit": pygame.Rect(170, 550, 254, 54),
        }

        self.labels = {
            "start": "開始遊戲",
            "settings": "設定",
            "credits": "製作團隊",
            "quit": "離開遊戲",
        }

        self.normal_color = (245, 240, 255)
        self.hover_color = (255, 225, 90)

    def draw(self):
        ctx = self.ctx
        screen = ctx.screen

        # 背景圖片已包含遊戲標題，不重複繪製
        if ctx.title_background is not None:
            screen.blit(ctx.title_background, (0, 0))
        else:
            screen.fill(ctx.colors["background"])

            ctx.draw_text(
                "Magic Academy",
                ctx.font_large,
                ctx.colors["gold"],
                350, 170
            )

        mouse_pos = pygame.mouse.get_pos()

        for name, rect in self.buttons.items():

            hovered = rect.collidepoint(mouse_pos)

            if hovered:
                # 半透明金黃色懸停效果
                overlay = pygame.Surface(
                    rect.size,
                    pygame.SRCALPHA
                )

                overlay.fill((255, 210, 70, 35))
                screen.blit(overlay, rect.topleft)

                color = self.hover_color
            else:
                color = self.normal_color

            # 文字置中於圖片按鈕外框
            ctx.draw_text(
                self.labels[name],
                ctx.font_medium,
                color,
                rect.centerx,
                rect.centery
            )

    def handle_event(self, event):

        if (
            event.type != pygame.MOUSEBUTTONDOWN
            or event.button != 1
        ):
            return None

        for name, rect in self.buttons.items():

            if rect.collidepoint(event.pos):

                if name == "quit":
                    return "quit"

                return {
                    "start": "class_selection",
                    "settings": "settings",
                    "credits": "credits",
                }[name]

        return None
