
import pygame
import json
from pathlib import Path

from ui.character_info_panel import CharacterInfoPanel
from ui.character_panel import CharacterPanel
from ui.inventory_panel import InventoryPanel
from ui.stat_allocation_panel import StatAllocationPanel

ROOT = Path(__file__).resolve().parents[1]


class PlayerMenu:

    TABS = [
        "角色資訊",
        "背包",
        "技能樹",
        "任務日誌",
        "世界地圖",
        "操作說明"
    ]

    def __init__(self, screen, draw_text=None):

        self.screen = screen
        self.draw_text = draw_text

        self.opened = False
        self.tab = 5
        self.hover = -1

        self.template = pygame.image.load(
            str(
                ROOT /
                "assets/ui/player_menu/player_menu_template.png"
            )
        ).convert_alpha()

        with open(
            ROOT / "data/ui/controls.json",
            encoding="utf-8"
        ) as f:
            self.controls = json.load(f)

        self.character_info_panel = CharacterInfoPanel()
        self.character_panel = CharacterPanel()

        self.inventory_panel = InventoryPanel()
        self.stat_allocation_panel = StatAllocationPanel()

        self.font_path = str(
            ROOT / "assets/fonts/NotoSansTC-Regular.ttf"
        )

        self.fonts = {}

        self.origin = (0, 0)
        self.scale = 1.0

    def font(self, size):

        size = max(10, int(size))

        if size not in self.fonts:
            font_path = self.font_path if Path(self.font_path).is_file() else None
            self.fonts[size] = pygame.font.Font(font_path, size)

        return self.fonts[size]

    def text(
        self,
        value,
        x,
        y,
        size=22,
        color=(240, 230, 205)
    ):

        surf = self.font(size).render(
            str(value),
            True,
            color
        )

        self.screen.blit(
            surf,
            (int(x), int(y))
        )

    def rect(self, x, y, w, h):

        ox, oy = self.origin
        s = self.scale

        return pygame.Rect(
            round(ox + x * s),
            round(oy + y * s),
            round(w * s),
            round(h * s)
        )

    def set_layout(self):

        sw, sh = self.screen.get_size()

        self.scale = min(
            sw / 1040,
            sh / 620,
            1.0
        )

        self.origin = (
            (sw - 1000 * self.scale) / 2,
            (sh - 580 * self.scale) / 2
        )

    def inventory_rect(self):
        sw, sh = self.screen.get_size()
        scale = min((sw-20)/1100,(sh-14)/620,1.25)
        w,h=round(1100*scale),round(620*scale)
        return pygame.Rect((sw-w)//2,(sh-h)//2,w,h)

    def inventory_back_rect(self):
        r=self.inventory_rect()
        scale=r.width/1100
        return pygame.Rect(r.x+round(28*scale),r.y+round(24*scale),
                           round(142*scale),round(47*scale))

    def open(self, tab=None):
        if tab is not None:
            self.tab = tab
        self.opened = True
        if self.tab == 1:
            self.inventory_panel.closed = False
            self.inventory_panel.back_requested = False
            self.inventory_panel.manager.reload()

    def close(self):
        self.opened = False
        self.inventory_panel.closed = False

    def return_from_inventory(self):
        """Keep the original V9.2 two-action design:

        Back returns to the character/player menu; Close exits to the world.
        Both keyboard and mouse use this single transition.
        """
        self.inventory_panel.back_requested = False
        self.inventory_panel.closed = False
        self.tab = 0
        self.opened = True

    def handle_key(self, key):
        if not self.opened:
            return False
        # Preserve V9.2: inventory Esc/Backspace go back to the player menu.
        # Tab toggles the entire player overlay from any page.
        if key == pygame.K_TAB:
            self.close()
            return True
        if self.tab == 1:
            if key == pygame.K_i:
                self.return_from_inventory()
                return True
            if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.return_from_inventory()
                return True
        elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            # Other tabs have no separate main-selection page; keep the
            # established layout, close to world instead of losing input.
            self.close()
            return True
        shortcuts = {pygame.K_c: 0, pygame.K_i: 1,
                     pygame.K_k: 2, pygame.K_m: 4, pygame.K_h: 5}
        if key in shortcuts:
            # Keep the V9.4 toggle shortcut while retaining V9.2 inventory Back.
            if self.tab == shortcuts[key]:
                self.close()
            else:
                self.open(shortcuts[key])
            return True
        if self.tab == 1 and self.inventory_panel.handle_key(key):
            if self.inventory_panel.back_requested:
                self.return_from_inventory()
            return True
        return False

    def handle_event(self, event):
        """滑鼠事件僅在玩家介面開啟時處理；鍵盤由 GameScene 發送。"""
        if not self.opened:
            return False

        self.set_layout()

        if self.tab != 1 and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect(875, 28, 85, 62).collidepoint(event.pos):
                self.close()
                return True

        if self.tab == 0 and self.stat_allocation_panel.handle_event(event):
            return True

        if self.tab == 1:
            self.inventory_panel.handle_event(event,self.inventory_rect())
            if self.inventory_panel.back_requested:
                self.return_from_inventory()
            elif self.inventory_panel.closed:
                self.close()
            return True

        if event.type == pygame.MOUSEMOTION:
            self.hover = -1
            for i in range(len(self.TABS)):
                rect = self.rect(35 + i * 155, 102, 145, 62)
                if rect.collidepoint(event.pos):
                    self.hover = i
                    break
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.TABS)):
                rect = self.rect(35 + i * 155, 102, 145, 62)
                if rect.collidepoint(event.pos):
                    self.open(i)  # Use the same initialization path as keyboard switching.
                    return True
            return True

        return True

    def draw(self):

        if not self.opened:
            return

        self.set_layout()

        sw, sh = self.screen.get_size()

        s = self.scale
        ox, oy = self.origin

        # 背景遮罩
        shade = pygame.Surface(
            (sw, sh),
            pygame.SRCALPHA
        )

        shade.fill((0, 0, 0, 155))
        self.screen.blit(shade, (0, 0))

        if self.tab == 1:
            self.inventory_panel.draw(self.screen,self.inventory_rect())
            return

        # 一般玩家選單
        template = pygame.transform.scale(
            self.template,
            (
                round(1000 * s),
                round(580 * s)
            )
        )

        self.screen.blit(
            template,
            (
                round(ox),
                round(oy)
            )
        )

        def txt(
            value,
            x,
            y,
            size=22,
            color=(240, 230, 205)
        ):

            self.text(
                value,
                ox + x * s,
                oy + y * s,
                size * s,
                color
            )

        txt(
            "冒 險 者 手 冊",
            390,
            43,
            28,
            (242, 212, 151)
        )

        # 所有分頁一致的關閉操作
        close_rect = self.rect(875, 28, 85, 62)
        pygame.draw.rect(self.screen, (92, 44, 62), close_rect, border_radius=7)
        pygame.draw.rect(self.screen, (242, 212, 151), close_rect, 2, border_radius=7)
        close_label = self.font(20 * s).render("關閉", True, (255, 233, 196))
        self.screen.blit(close_label, close_label.get_rect(center=close_rect.center))

        # 分頁按鈕
        for i, name in enumerate(self.TABS):

            r = self.rect(
                35 + i * 155,
                102,
                145,
                62
            )

            if i == self.tab:
                color = (215, 165, 75, 110)

            elif i == self.hover:
                color = (255, 220, 120, 95)

            else:
                color = None

            if color:

                overlay = pygame.Surface(
                    r.size,
                    pygame.SRCALPHA
                )

                overlay.fill(color)

                self.screen.blit(
                    overlay,
                    r.topleft
                )

            if i == self.tab or i == self.hover:

                pygame.draw.rect(
                    self.screen,
                    (248, 215, 128),
                    r,
                    max(1, round(2 * s))
                )

            label = self.font(19 * s).render(
                name,
                True,
                (255, 235, 185)
            )

            self.screen.blit(
                label,
                label.get_rect(center=r.center)
            )

        # 內容標題
        txt(
            self.TABS[self.tab],
            75,
            208,
            27,
            (242, 212, 151)
        )

        pygame.draw.line(
            self.screen,
            (145, 118, 93),
            (
                round(ox + 70 * s),
                round(oy + 252 * s)
            ),
            (
                round(ox + 930 * s),
                round(oy + 252 * s)
            ),
            max(1, round(2 * s))
        )

        # 操作說明
        if self.tab == 5:

            for i, (key, description) in enumerate(
                self.controls
            ):

                y = 273 + i * 27

                txt(
                    key,
                    85,
                    y,
                    17,
                    (245, 205, 135)
                )

                txt(
                    description,
                    370,
                    y,
                    17
                )

        # 角色資訊
        elif self.tab == 0:

            # 角色資訊與配點不再同時繪製，避免半透明面板互相覆蓋。
            self.stat_allocation_panel.draw(
                self.screen,
                self.rect(58, 260, 880, 280)
            )

        # 技能樹
        elif self.tab == 2:

            txt("技能樹", 85, 280, 22)

            txt(
                "職業技能與技能點數將顯示在此。",
                85,
                335,
                19
            )

        # 任務日誌
        elif self.tab == 3:

            txt("任務日誌", 85, 280, 22)

            txt(
                "主線、支線及已完成任務將顯示在此。",
                85,
                335,
                19
            )

        # 世界地圖
        elif self.tab == 4:

            txt("世界地圖", 85, 280, 22)

            txt(
                "已探索地區與傳送點將顯示在此。",
                85,
                335,
                19
            )

        txt(
            "Tab 關閉 / Esc 返回",
            765,
            507,
            15,
            (188, 176, 159)
        )
