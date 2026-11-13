import pygame
from scenes.scene_base import BaseScene


class CreditsScene(BaseScene):

    def __init__(self, ctx):
        super().__init__(ctx)

        self.panel = pygame.Rect(280, 95, 720, 540)
        self.back_button = pygame.Rect(475, 545, 330, 58)

        self.gold = (235, 190, 95)
        self.bright_gold = (255, 225, 110)
        self.white = (245, 240, 255)
        self.gray = (170, 180, 205)

    def draw(self):
        ctx = self.ctx
        screen = ctx.screen
        mouse = pygame.mouse.get_pos()

        screen.fill((15, 13, 35))

        # 背景魔法圓環
        pygame.draw.circle(
            screen, (35, 30, 70), (640, 360), 330
        )
        pygame.draw.circle(
            screen, (75, 60, 115), (640, 360), 310, 2
        )

        # 面板陰影
        pygame.draw.rect(
            screen, (7, 7, 20),
            self.panel.move(8, 10),
            border_radius=18
        )

        # 主面板
        pygame.draw.rect(
            screen, (28, 24, 57),
            self.panel,
            border_radius=18
        )
        pygame.draw.rect(
            screen, self.gold,
            self.panel, 3,
            border_radius=18
        )

        # 內框
        pygame.draw.rect(
            screen, (85, 68, 120),
            self.panel.inflate(-18, -18),
            1,
            border_radius=14
        )

        ctx.draw_text(
            "製作團隊",
            ctx.font_large,
            self.bright_gold,
            640, 165
        )

        pygame.draw.line(
            screen, self.gold,
            (400, 220), (880, 220), 2
        )

        ctx.draw_text(
            "Magic Academy",
            ctx.font_large,
            self.white,
            640, 285
        )

        ctx.draw_text(
            "The Lost Ancient Magic",
            ctx.font_medium,
            self.bright_gold,
            640, 332
        )

        ctx.draw_text(
            "魔法學院 RPG",
            ctx.font_medium,
            self.white,
            640, 395
        )

        ctx.draw_text(
            "Version 0.1.0",
            ctx.font_small,
            self.gray,
            640, 455
        )

        hovered = self.back_button.collidepoint(mouse)

        pygame.draw.rect(
            screen,
            (105, 82, 42) if hovered else (45, 38, 80),
            self.back_button,
            border_radius=12
        )

        pygame.draw.rect(
            screen,
            self.bright_gold if hovered else self.gold,
            self.back_button,
            2,
            border_radius=12
        )

        ctx.draw_text(
            "返回主選單",
            ctx.font_medium,
            self.bright_gold if hovered else self.white,
            self.back_button.centerx,
            self.back_button.centery
        )

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            return "title"
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if self.back_button.collidepoint(event.pos):
                return "title"

        return None
