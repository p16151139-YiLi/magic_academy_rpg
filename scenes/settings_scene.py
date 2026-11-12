import pygame
from scenes.scene_base import BaseScene


class SettingsScene(BaseScene):

    PANEL = pygame.Rect(270, 90, 740, 550)

    SLIDER_X = 450
    SLIDER_WIDTH = 380
    MUSIC_Y = 300
    SFX_Y = 415

    def __init__(self, ctx):
        super().__init__(ctx)
        self.back_button = pygame.Rect(475, 515, 330, 62)

        self.dragging = None

        self.gold = (235, 190, 95)
        self.bright_gold = (255, 230, 120)
        self.white = (245, 240, 255)
        self.muted = (170, 175, 205)

    def draw_background(self):
        screen = self.ctx.screen
        screen.fill((15, 13, 35))

        # 魔法風格背景裝飾
        pygame.draw.circle(
            screen, (32, 27, 65), (640, 360), 310
        )
        pygame.draw.circle(
            screen, (75, 57, 110), (640, 360), 300, 2
        )
        pygame.draw.circle(
            screen, (48, 42, 90), (640, 360), 270, 1
        )

        # 主面板陰影
        shadow = self.PANEL.move(8, 10)
        pygame.draw.rect(
            screen, (8, 7, 20), shadow, border_radius=18
        )

        # 主面板
        pygame.draw.rect(
            screen, (28, 24, 57),
            self.PANEL, border_radius=18
        )

        pygame.draw.rect(
            screen, self.gold,
            self.PANEL, 3, border_radius=18
        )

        inner = self.PANEL.inflate(-18, -18)
        pygame.draw.rect(
            screen, (88, 69, 122),
            inner, 1, border_radius=14
        )

        # 標題下方裝飾線
        pygame.draw.line(
            screen, self.gold,
            (400, 205), (880, 205), 2
        )

        pygame.draw.circle(
            screen, self.bright_gold, (640, 205), 5
        )

    def draw_slider(self, y, value, active=False):
        screen = self.ctx.screen

        value = max(0.0, min(1.0, float(value)))
        start = self.SLIDER_X
        end = start + self.SLIDER_WIDTH
        knob_x = start + round(self.SLIDER_WIDTH * value)

        # 滑桿底座
        pygame.draw.line(
            screen, (65, 60, 100),
            (start, y), (end, y), 12
        )

        # 金色進度
        pygame.draw.line(
            screen, self.bright_gold if active else self.gold,
            (start, y), (knob_x, y), 8
        )

        # 滑桿圓形控制點
        if active:
            pygame.draw.circle(
                screen, (115, 86, 38),
                (knob_x, y), 19
            )

        pygame.draw.circle(
            screen,
            self.bright_gold if active else self.white,
            (knob_x, y), 13
        )

        pygame.draw.circle(
            screen, self.gold,
            (knob_x, y), 13, 2
        )

    def draw_button(self, rect, label, mouse):
        screen = self.ctx.screen
        hovered = rect.collidepoint(mouse)

        background = (
            (102, 82, 43) if hovered
            else (47, 39, 82)
        )

        border = self.bright_gold if hovered else self.gold
        text_color = self.bright_gold if hovered else self.white

        pygame.draw.rect(
            screen, background, rect, border_radius=12
        )
        pygame.draw.rect(
            screen, border, rect, 2, border_radius=12
        )

        self.ctx.draw_text(
            label,
            self.ctx.font_medium,
            text_color,
            rect.centerx,
            rect.centery
        )

    def draw(self):
        ctx = self.ctx
        mouse = pygame.mouse.get_pos()

        self.draw_background()

        ctx.draw_text(
            "遊戲設定",
            ctx.font_large,
            self.bright_gold,
            640, 155
        )

        ctx.draw_text(
            "音樂音量",
            ctx.font_medium,
            self.white,
            510, 250
        )

        ctx.draw_text(
            f"{round(ctx.music_volume * 100)}%",
            ctx.font_small,
            self.bright_gold,
            795, 250
        )

        music_hover = (
            self.dragging == "music"
            or (
                self.SLIDER_X - 20 <= mouse[0]
                <= self.SLIDER_X + self.SLIDER_WIDTH + 20
                and abs(mouse[1] - self.MUSIC_Y) <= 20
            )
        )

        self.draw_slider(
            self.MUSIC_Y,
            ctx.music_volume,
            music_hover
        )

        ctx.draw_text(
            "音效音量",
            ctx.font_medium,
            self.white,
            510, 365
        )

        ctx.draw_text(
            f"{round(ctx.sfx_volume * 100)}%",
            ctx.font_small,
            self.bright_gold,
            795, 365
        )

        sfx_hover = (
            self.dragging == "sfx"
            or (
                self.SLIDER_X - 20 <= mouse[0]
                <= self.SLIDER_X + self.SLIDER_WIDTH + 20
                and abs(mouse[1] - self.SFX_Y) <= 20
            )
        )

        self.draw_slider(
            self.SFX_Y,
            ctx.sfx_volume,
            sfx_hover
        )


        self.draw_button(
            self.back_button,
            "返回主選單",
            mouse
        )

    def slider_at(self, pos):
        x, y = pos

        if not (
            self.SLIDER_X - 20 <= x
            <= self.SLIDER_X + self.SLIDER_WIDTH + 20
        ):
            return None

        if abs(y - self.MUSIC_Y) <= 20:
            return "music"

        if abs(y - self.SFX_Y) <= 20:
            return "sfx"

        return None

    def update_slider(self, pos, slider):
        value = (pos[0] - self.SLIDER_X) / self.SLIDER_WIDTH
        value = max(0.0, min(1.0, value))

        if slider == "music":
            self.ctx.music_volume = value
            self.ctx.audio.set_music_volume(value)

        elif slider == "sfx":
            self.ctx.sfx_volume = value
            self.ctx.audio.set_sfx_volume(value)

    def handle_event(self, event):



        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                return None

            slider = self.slider_at(event.pos)

            if slider is not None:
                self.dragging = slider
                self.update_slider(event.pos, slider)
                return None


            if self.back_button.collidepoint(event.pos):
                self.ctx.save_settings()
                return "title"

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging and event.buttons[0]:
                self.update_slider(event.pos, self.dragging)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging:
                self.update_slider(event.pos, self.dragging)
                self.dragging = None
                self.ctx.save_settings()

        return None
