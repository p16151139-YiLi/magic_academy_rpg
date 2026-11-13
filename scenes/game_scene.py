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
        self._loading_map_ref = None
        self._loading_npc_queue = []
        self._load_error = ""
        self._draw_error = ""

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
        # The browser may lose KEYDOWN when focus changes. Poll only rising
        # edges, never repeat an action already delivered by KEYDOWN.
        self._e_keydown_seen = False
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
        """Load a map and its NPC sprites over multiple browser frames."""
        if self.map_loaded:
            return True
        # Do not repeatedly decode a broken asset every frame. The error
        # screen remains responsive; R performs an explicit retry.
        if self._load_error:
            return False
        try:
            if self._loading_map_ref is not self.map_data:
                self.map_renderer.begin_load(self.map_data)
                self._loading_map_ref = self.map_data
                # Keep all original NPC art; only spread sprite decoding over frames.
                self._loading_npc_queue = list(dict.fromkeys(
                    npc['sprite'] for npc in self.map_data.get('npcs', [])))
            if self.map_renderer.loading:
                self.map_renderer.step_load()
                return False
            if self._loading_npc_queue:
                self.npc_shop.sprites.frames(self._loading_npc_queue.pop(0))
                return False
            self.map_loaded = True
            self._loading_map_ref = None
            self._load_error = ""
            return True
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._load_error = f"載入失敗：{type(exc).__name__}: {exc}"
            return False

    def draw_loading(self, screen):
        """Always show a live loading/error state instead of a frozen last frame."""
        screen.fill((24, 27, 46))
        font = self.ctx.font_medium
        small = self.ctx.font_small
        label = self.map_data.get('name', '新場景')
        if self._load_error:
            lines = ['場景載入異常', self._load_error[:65], '按 R 重試，Esc 返回主選單']
        else:
            map_progress = self.map_renderer.load_progress
            total_npcs = len(set(n['sprite'] for n in self.map_data.get('npcs', [])))
            done_npcs = total_npcs - len(self._loading_npc_queue)
            percent = int(100 * (map_progress * 0.8 + (done_npcs / max(1,total_npcs)) * 0.2))
            lines = ['正在載入：' + label, f'地圖與 NPC 素材 {min(percent,100)}%',
                     '按 Esc 可以返回主選單']
        for idx, line in enumerate(lines):
            rendered = (font if idx == 0 else small).render(line, True, (244, 227, 197))
            screen.blit(rendered, rendered.get_rect(center=(screen.get_width()//2,
                                                            screen.get_height()//2 - 55 + idx*48)))

    def draw(self):
        if self._draw_error:
            self.draw_recovery_screen()
            return
        try:
            self._draw_game_world()
        except Exception as exc:
            # In a browser a draw exception otherwise kills the async loop and
            # leaves the last frame on screen, which looks like a hard freeze.
            import traceback
            if self._draw_error != repr(exc):
                traceback.print_exc()
            self._draw_error = repr(exc)
            self.draw_recovery_screen()

    def draw_recovery_screen(self):
        """A render error must not trap the user on an unusable frozen frame."""
        screen=self.ctx.screen
        screen.fill((30, 27, 50))
        lines=('畫面繪製發生錯誤', self._draw_error[:75],
               '按 R 重新繪製；Esc 返回主選單')
        for idx,line in enumerate(lines):
            rendered=self.ctx.font_small.render(line,True,(248,218,187))
            screen.blit(rendered,rendered.get_rect(
                center=(screen.get_width()//2, 260+idx*55)))

    def _draw_game_world(self):
        ctx = self.ctx
        screen = ctx.screen
        if not self.map_loaded:
            self.draw_loading(screen)
            return

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
        build_tag = ctx.font_small.render("V9.5.1 AUDIT FIX", True, (243, 210, 123))
        screen.blit(build_tag, (screen.get_width() // 2 - build_tag.get_width() // 2, 7))

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
            # World interaction first when next to a door. Give feedback even
            # when the key was received OUTSIDE the actual approach zone.
            if self.player_world.find_nearby_exit() is not None:
                result = self.player_world.interact()
                if result is False:
                    self.player_world.show_message("入口互動失敗，請再按 E", 2.5)
            elif not self.npc_shop.interact():
                if self.map_id == "academy_entrance":
                    self.player_world.show_message(
                        "E 鍵已收到：請走到大廳木門前的紫色地毯", 2.8)
                else:
                    self.player_world.show_message(
                        "E 鍵已收到：請靠近人物或入口", 2.2)
            return True
        return False

    def _poll_keyboard(self):
        """Restore V9.2 browser fallback without double-dispatching keys.

        Rising edges only; a KEYDOWN already routed in the current frame
        suppresses the matching edge. KEYUP of E must not interact twice.
        """
        watched = (pygame.K_TAB, pygame.K_ESCAPE, pygame.K_c, pygame.K_i,
                   pygame.K_k, pygame.K_m, pygame.K_h, pygame.K_e,
                   pygame.K_RETURN, pygame.K_SPACE, pygame.K_UP, pygame.K_DOWN,
                   pygame.K_w, pygame.K_s, pygame.K_u, pygame.K_BACKSPACE,
                   pygame.K_1, pygame.K_2, pygame.K_3,
                   pygame.K_4, pygame.K_5, pygame.K_6,
                   pygame.K_LEFT, pygame.K_RIGHT)
        state = pygame.key.get_pressed()
        current = {key for key in watched if state[key]}
        for key in current - self._previous_game_keys - self._handled_key_events:
            self._game_key(key)
            if key == pygame.K_e:
                self._e_keydown_seen = True
        self._previous_game_keys = current
        self._handled_key_events.clear()

    def update(self, dt):
        # Important: do not start gameplay or NPC AI against a half-loaded map.
        if not self.map_loaded:
            self.ensure_map_loaded()
            return
        self._poll_keyboard()
        if not self.map_loaded:  # a key may have just changed the map
            return
        self.player_world.update(dt)
        self.npc_shop.update(dt)
        self.quickbar.update(dt)

    def handle_event(self, event):
        if not getattr(self, 'map_loaded', True):
            # Keep the loading error screen usable even when an asset is bad.
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return "title"
                if event.key == pygame.K_r and self._load_error:
                    self._load_error = ""
                    self._loading_map_ref = None
                    self._loading_npc_queue = []
            return None
        if getattr(self, '_draw_error', ''):
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._draw_error = ""
                elif event.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
                    # If the error originated in a panel, allow the panel to
                    # close and the normal world to recover first.
                    if self.player_menu.opened:
                        self.player_menu.close()
                        self._draw_error = ""
                    else:
                        return "title"
            return None
        if event.type == pygame.KEYDOWN:
            # Some browser/IME layouts expose printable E via unicode while
            # the key identifier varies; normalize it before dispatching.
            key = event.key
            if (key == pygame.K_e or
                    str(getattr(event, "unicode", "")).lower() == "e"):
                key = pygame.K_e
                self._e_keydown_seen = True
            if not getattr(event, "repeat", 0):
                self._handled_key_events.add(key)
                self._game_key(key)
            return None
        if event.type == pygame.KEYUP and event.key == pygame.K_e:
            # If browser focus lost KEYDOWN, use KEYUP as a single fallback.
            if (not self._e_keydown_seen and not getattr(getattr(self, "player_menu", None), "opened", False)
                    and not getattr(getattr(self, "npc_shop", None), "shop", None)
                    and not getattr(getattr(self, "npc_shop", None), "dialogue", None)):
                self._game_key(pygame.K_e)
            self._e_keydown_seen = False
            return None
        # Overlay has priority: dialogue/shop > player menu > game world.
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
            if self.player_world.click_exit_artwork(event.pos):
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
