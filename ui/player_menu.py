
import pygame
import json
from pathlib import Path

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
        self.tab = -1  # -1 is the real six-button parent menu.
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

        # The unified stat overview now draws character information directly.
        # Do not allocate an unused second panel/font set on every game entry.
        self.character_info_panel = None
        self.character_panel = CharacterPanel()

        self.inventory_panel = InventoryPanel()
        self.stat_allocation_panel = StatAllocationPanel()

        self.font_path = str(
            ROOT / "assets/fonts/NotoSansTC-Regular.ttf"
        )

        self.fonts = {}

        self.origin = (0, 0)
        self.scale = 1.0
        self._shade_surface = None
        self._shade_size = None
        self._template_scaled = None
        self._template_scaled_size = None
        self._text_cache = {}
        self._tab_overlay_cache = {}
        self._info_canvas = None
        self._info_target = None

    def font(self, size):

        size = max(10, int(size))

        if size not in self.fonts:
            font_path = self.font_path if Path(self.font_path).is_file() else None
            self.fonts[size] = pygame.font.Font(font_path, size)

        return self.fonts[size]

    def _cached_text(self, value, size, color):
        key = (str(value), max(10,int(size)), tuple(color))
        image = self._text_cache.get(key)
        if image is None:
            image = self.font(key[1]).render(key[0], True, key[2])
            if len(self._text_cache) >= 384:
                self._text_cache.clear()
            self._text_cache[key] = image
        return image

    def text(
        self,
        value,
        x,
        y,
        size=22,
        color=(240, 230, 205)
    ):

        surf = self._cached_text(value, size, color)

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
        elif not self.opened:
            self.tab = -1
        self.opened = True
        if self.tab == 0 and hasattr(self, "stat_allocation_panel"):
            self.stat_allocation_panel.invalidate()
        if self.tab == 1:
            self.inventory_panel.closed = False
            self.inventory_panel.back_requested = False
            self.inventory_panel.manager.reload()

    def close(self):
        self.opened = False
        self.tab = -1
        self.inventory_panel.closed = False

    def return_from_inventory(self):
        """Keep the original V9.2 two-action design:

        Back returns to the character/player menu; Close exits to the world.
        Both keyboard and mouse use this single transition.
        """
        self.inventory_panel.back_requested = False
        self.inventory_panel.closed = False
        self.tab = -1
        self.opened = True

    def return_home(self):
        """Back means the six-item parent menu; never jump into character info."""
        self.inventory_panel.back_requested = False
        self.inventory_panel.closed = False
        self.tab = -1
        self.opened = True

    def handle_key(self, key):
        if not self.opened:
            return False
        if key == pygame.K_TAB:
            self.close()
            return True
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            if self.tab == -1:
                self.close()
            else:
                self.return_home()
            return True
        shortcuts = {pygame.K_c: 0, pygame.K_i: 1,
                     pygame.K_k: 2, pygame.K_m: 4, pygame.K_h: 5}
        if key in shortcuts:
            requested = shortcuts[key]
            if requested == self.tab:
                self.return_home()
            else:
                self.open(requested)
            return True
        if self.tab == 1 and self.inventory_panel.handle_key(key):
            if self.inventory_panel.back_requested:
                self.return_home()
            elif self.inventory_panel.closed:
                self.close()
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
            if self.tab >= 0 and self.rect(744, 492, 208, 57).collidepoint(event.pos):
                self.return_home()
                return True

        if self.tab == 0 and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            destination=self.rect(58,260,880,226)
            if destination.collidepoint(event.pos):
                logical_x=(event.pos[0]-destination.x)*880/max(1,destination.width)
                logical_y=(event.pos[1]-destination.y)*226/max(1,destination.height)
                logical=pygame.event.Event(pygame.MOUSEBUTTONDOWN,{'button':1,
                    'pos':(round(logical_x),round(logical_y))})
                if self.stat_allocation_panel.handle_event(logical):
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
        if self._shade_size != (sw,sh):
            self._shade_surface = pygame.Surface((sw,sh),pygame.SRCALPHA)
            self._shade_surface.fill((0,0,0,155))
            self._shade_size = (sw,sh)
        self.screen.blit(self._shade_surface,(0,0))

        if self.tab == 1:
            self.inventory_panel.draw(self.screen,self.inventory_rect())
            return

        # 一般玩家選單
        template_size=(round(1000*s),round(580*s))
        if template_size != self._template_scaled_size:
            self._template_scaled = pygame.transform.scale(self.template,template_size)
            self._template_scaled_size=template_size
        self.screen.blit(
            self._template_scaled,
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
        close_label = self._cached_text('關閉', 20 * s, (255, 233, 196))
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

                overlay_key = (r.size, color)
                overlay = self._tab_overlay_cache.get(overlay_key)
                if overlay is None:
                    overlay = pygame.Surface(r.size, pygame.SRCALPHA)
                    overlay.fill(color)
                    self._tab_overlay_cache[overlay_key] = overlay
                self.screen.blit(overlay, r.topleft)

            if i == self.tab or i == self.hover:

                pygame.draw.rect(
                    self.screen,
                    (248, 215, 128),
                    r,
                    max(1, round(2 * s))
                )

            label_key = (name, max(10, int(19*s)), (255,235,185))
            label = self._text_cache.get(label_key)
            if label is None:
                label = self.font(label_key[1]).render(name,True,label_key[2])
                self._text_cache[label_key] = label

            self.screen.blit(
                label,
                label.get_rect(center=r.center)
            )

        # 內容標題
        txt(
            self.TABS[self.tab] if self.tab >= 0 else "玩家選單",
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

        # Parent selection: keep all six original button positions unchanged.
        if self.tab == -1:
            txt("請選擇上方功能", 85, 290, 25)
            txt("Tab：返回遊戲    Esc：關閉選單", 85, 355, 19)

        # 操作說明
        elif self.tab == 5:

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
            try:
                # Render at stable logical resolution, then scale the whole
                # page to the current window. The old direct draw raised on
                # screens <620 high because height fell under 220 pixels.
                if self._info_canvas is None:
                    self._info_canvas = pygame.Surface((880, 226), pygame.SRCALPHA)
                self._info_canvas.fill((0, 0, 0, 0))
                self.stat_allocation_panel.draw(self._info_canvas,
                                                pygame.Rect(0, 0, 880, 226))
                dest = self.rect(58, 260, 880, 226)
                if dest.size != (880, 226):
                    scaled = pygame.transform.scale(self._info_canvas, dest.size)
                else:
                    scaled = self._info_canvas
                self.screen.blit(scaled, dest.topleft)
            except Exception as exc:
                # Report a precise source rather than an empty SDL error.
                raise RuntimeError(
                    "CharacterInfoPanel/StatAllocationPanel draw failed "
                    f"({type(exc).__name__}: {repr(exc)})"
                ) from exc

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

        if self.tab >= 0:
            back = self.rect(744, 492, 208, 57)
            pygame.draw.rect(self.screen, (67, 49, 91), back, border_radius=7)
            pygame.draw.rect(self.screen, (242, 212, 151), back, 2, border_radius=7)
            label = self._cached_text('返回選單', max(12, round(18*s)), (255, 233, 196))
            self.screen.blit(label, label.get_rect(center=back.center))
        else:
            txt("Tab 關閉 / Esc 返回遊戲", 700, 507, 15, (188, 176, 159))
