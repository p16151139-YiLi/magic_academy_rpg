# PLAYER_MENU_INTEGRATION_V1
from ui.player_menu import PlayerMenu

from pathlib import Path

import pygame

from scenes.scene_base import BaseScene
from systems.map_manager import MapManager
from systems.map_renderer import MapRenderer
from systems.camera import Camera


class GameScene(BaseScene):

    def __init__(self, ctx):
        super().__init__(ctx)

        self.root = Path(__file__).resolve().parents[1]

        # 地圖管理器
        self.map_manager = MapManager(self.root)

        # 地圖渲染器
        self.map_renderer = MapRenderer(self.root)

        # 攝影機
        self.camera = Camera(
            ctx.screen.get_width(),
            ctx.screen.get_height()
        )

        self.map_id = "academy_entrance"

        # 讀取地圖 JSON
        self.map_data = self.map_manager.load_map(
            self.map_id
        )

        # 取得角色預定出生位置
        self.spawn = self.map_manager.get_spawn()

        # 依出生位置設定攝影機
        self.camera.follow(
            self.spawn[0],
            self.spawn[1],
            self.map_data["width"],
            self.map_data["height"]
        )

        # 延後圖片載入，確保顯示畫面已初始化
        self.map_loaded = False

        # 返回按鈕
        self.back_button = pygame.Rect(
            18, 18, 190, 48
        )

        # 地圖資訊面板
        self.info_panel = pygame.Rect(
            18, 80, 280, 84
        )
        # 初始化玩家介面
        self.player_menu = PlayerMenu(self.ctx.screen)
        from systems.quickbar import Quickbar
        self.quickbar = Quickbar()
        self.player_menu.inventory_panel.quickbar = self.quickbar
        self._previous_game_keys = set()
        self._handled_key_events = set()
        self.shortcut_hint_open = False

        # STAGE4_PLAYER_WORLD_INTEGRATION
        from systems.player_world_bridge import PlayerWorldBridge
        self.player_world = PlayerWorldBridge(self)
        self.player = self.player_world.player
        from systems.npc_shop_system import NPCShopSystem
        self.npc_shop = NPCShopSystem(self)

    def ensure_map_loaded(self):
        """首次繪製時載入地圖圖片。"""

        if not self.map_loaded:
            self.map_renderer.load(self.map_data)
            self.map_loaded = True

    def draw(self):
        ctx = self.ctx
        screen = ctx.screen

        self.ensure_map_loaded()

        screen.fill((20, 25, 30))

        # 依序繪製地圖圖層
        self.map_renderer.draw_ground(
            screen, self.camera
        )

        self.map_renderer.draw_objects(
            screen, self.camera
        )
        self.map_renderer.draw_decals(screen, self.camera)

        # 前景遮擋層
        # 玩家繪製於物件與前景之間
        # 角色依腳部座標排序：走到 NPC 前方時會自然遮住對方。
        self.npc_shop.draw_npcs(screen, include_player=True)
        self.player_world.draw(screen, include_player=False)

        self.map_renderer.draw_foreground(
            screen, self.camera
        )



        # ----------------------------------
        # 返回主選單按鈕
        # ----------------------------------

        mouse = pygame.mouse.get_pos()
        hovered = self.back_button.collidepoint(mouse)

        pygame.draw.rect(
            screen,
            (65, 55, 95) if hovered else (30, 28, 55),
            self.back_button,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            (235, 190, 95),
            self.back_button,
            2,
            border_radius=8
        )

        ctx.draw_text(
            "返回主選單",
            ctx.font_small,
            (245, 240, 255),
            self.back_button.centerx,
            self.back_button.centery
        )

        # ----------------------------------
        # 地圖資訊
        # ----------------------------------

        pygame.draw.rect(
            screen,
            (28, 30, 48),
            self.info_panel,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            (150, 135, 90),
            self.info_panel,
            2,
            border_radius=8
        )

        ctx.draw_text(
            self.map_data["name"],
            ctx.font_small,
            (245, 225, 170),
            self.info_panel.centerx,
            108
        )

        ctx.draw_text(
            "第一章：魔法學院",
            ctx.font_small,
            (210, 215, 235),
            self.info_panel.centerx,
            140
        )
        self.draw_shortcut_hint(screen)
        if not self.player_menu.opened and not self.npc_shop.shop and not self.npc_shop.dialogue:
            self.quickbar.draw(screen)
        # 地圖與場景繪製完成後，顯示玩家介面
        self.player_menu.draw()
        self.npc_shop.draw_overlay(screen)
        # Visible build number makes a stale GitHub Pages cache easy to spot.
        build_tag = ctx.font_small.render("V9.1 Hall Fix", True, (197, 186, 164))
        screen.blit(build_tag, (screen.get_width() - build_tag.get_width() - 10, 4))

    def shortcut_button_rect(self):
        return pygame.Rect(self.ctx.screen.get_width() - 160, 12, 146, 34)

    def draw_shortcut_hint(self, screen):
        """右上角可收合的操作說明，避免遮住入口標記。"""
        if self.player_menu.opened:
            return
        font = self.ctx.font_small
        btn = self.shortcut_button_rect()
        pygame.draw.rect(screen, (30, 29, 54), btn, border_radius=7)
        pygame.draw.rect(screen, (210, 180, 112), btn, 2, border_radius=7)
        label = font.render("操作提示  -" if self.shortcut_hint_open else "操作提示  +", True, (255, 234, 191))
        screen.blit(label, label.get_rect(center=btn.center))
        if not self.shortcut_hint_open:
            return
        rows = ["WASD / 方向鍵  移動", "E  互動    I  背包", "C  角色    K  技能", "M  地圖    Tab  選單", "1～6 使用右下快捷道具", "Esc  返回"]
        rendered = [font.render(row, True, (238, 235, 223)) for row in rows]
        width = max(item.get_width() for item in rendered) + 26
        panel = pygame.Rect(screen.get_width() - width - 14, 52, width, 12 + len(rows) * 28)
        pygame.draw.rect(screen, (25, 29, 48), panel, border_radius=9)
        pygame.draw.rect(screen, (159, 144, 109), panel, 2, border_radius=9)
        for i, item in enumerate(rendered):
            screen.blit(item, (panel.x + 13, panel.y + 7 + i * 28))

    def _game_key(self, key):
        """One keyboard route for physical KEYDOWN and browser state polling."""
        if self.npc_shop.shop or self.npc_shop.dialogue:
            self.npc_shop.handle_key(key)
            return True
        if self.player_menu.opened:
            return bool(self.player_menu.handle_key(key))
        if key in self.quickbar.KEYS:
            self.quickbar.use(key-pygame.K_1)
            return True
        if key == pygame.K_TAB:
            self.player_menu.open()
            return True
        shortcuts = {pygame.K_c: 0, pygame.K_i: 1,
                     pygame.K_k: 2, pygame.K_m: 4, pygame.K_h: 5}
        if key in shortcuts:
            self.player_menu.open(shortcuts[key])
            return True
        if key == pygame.K_ESCAPE:
            # 在世界畫面按 Esc 顯示選單，不返回標題畫面。
            self.player_menu.open(5)
            return True
        if key == pygame.K_e:
            # Door interaction must not be swallowed by an idle NPC nearby.
            # Active shop/dialogue windows are already handled above.
            if self.player_world.find_nearby_exit() is not None:
                self.player_world.interact()
            elif not self.npc_shop.interact():
                self.player_world.interact()
            return True
        return False

    def _poll_keyboard(self):
        """KEYDOWN is primary; key-state poll only repairs lost browser events."""
        watched = (pygame.K_TAB, pygame.K_ESCAPE, pygame.K_c, pygame.K_i,
                   pygame.K_k, pygame.K_m, pygame.K_h, pygame.K_e,
                   pygame.K_RETURN, pygame.K_SPACE, pygame.K_UP, pygame.K_DOWN,
                   pygame.K_w, pygame.K_s, pygame.K_u, pygame.K_BACKSPACE,
                   pygame.K_1, pygame.K_2, pygame.K_3,
                   pygame.K_4, pygame.K_5, pygame.K_6,
                   pygame.K_LEFT, pygame.K_RIGHT)
        state = pygame.key.get_pressed()
        current = {key for key in watched if state[key]}
        newly_pressed = current - self._previous_game_keys - self._handled_key_events
        self._previous_game_keys = current
        for key in newly_pressed:
            self._game_key(key)
        self._handled_key_events.clear()

    def update(self, dt):
        self._poll_keyboard()
        self.player_world.update(dt)
        self.npc_shop.update(dt)
        self.quickbar.update(dt)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            # Do not let Pygbag/desktop short taps disappear between frames.
            if getattr(event, "repeat", 0) == 0:
                if event.key not in self._handled_key_events:
                    self._handled_key_events.add(event.key)
                    self._game_key(event.key)
            return None
        # 選單開啟時，滑鼠事件交由選單處理。
        if self.npc_shop.shop or self.npc_shop.dialogue:
            self.npc_shop.handle_event(event)
            return None
        if self.player_menu.opened:
            self.player_menu.handle_event(event)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.quickbar.click(event.pos):
                return None
            if self.shortcut_button_rect().collidepoint(event.pos):
                self.shortcut_hint_open = not self.shortcut_hint_open
                return None
            if self.back_button.collidepoint(event.pos):
                return "title"
            if self.player_world.click_interaction_prompt(event.pos):
                return None
            if self.player_world.click_location_marker(event.pos):
                return None

        return None

    # INVENTORY_SERVICE_INTEGRATION_V1

    def get_item_service(self):
        from systems.item_service import ItemService

        if not hasattr(self, "_item_service"):
            self._item_service = ItemService()

        return self._item_service

    def inventory_snapshot(self):
        return self.get_item_service().refresh()

    def give_player_item(self, item_id, amount=1):
        return self.get_item_service().give_item(
            item_id, amount
        )

    def remove_player_item(self, item_id, amount=1):
        return self.get_item_service().take_item(
            item_id, amount
        )

    def use_player_item(self, item_id):
        return self.get_item_service().use_item(item_id)

    def equip_player_item(self, item_id):
        return self.get_item_service().equip_item(item_id)

    def unequip_player_item(self, slot):
        return self.get_item_service().unequip_item(slot)

    def get_player_resources(self):
        data = self.get_item_service().get_player()
        return {
            "hp": data.get("hp", 0),
            "max_hp": data.get("max_hp", 0),
            "mp": data.get("mp", 0),
            "max_mp": data.get("max_mp", 0)
        }

    def get_player_equipment_bonuses(self):
        return (
            self.get_item_service()
            .get_equipment_bonuses()
        )
