
import json
from pathlib import Path
import pygame
from systems.save_store import read_json

from systems.player_entity import PlayerEntity


class PlayerWorldBridge:

    def __init__(self, scene):
        self.scene = scene

        root = Path(__file__).resolve().parents[1]
        player_file = root / "data/player/player_data.json"

        # 優先使用本次職業選擇結果
        class_id = getattr(
            scene.ctx,
            "selected_class_id",
            None
        )

        # 沒有本次選擇時才讀取存檔
        if not class_id:
            class_id = "balanced_mage"

            if player_file.exists():
                try:
                    data = read_json(player_file, {})
                    class_id = data.get(
                        "class_id",
                        class_id
                    )
                except (OSError, ValueError):
                    pass

        x, y = scene.map_manager.get_spawn()

        self.player = PlayerEntity(
            x=x,
            y=y,
            class_id=class_id
        )

        self.transition_cooldown = 0.0
        self.show_collision_debug = False
        self.fade_alpha = 0
        self.message = ""
        self.message_timer = 0.0

        self.nearby_exit = None
        self._interaction_prompt_rect = None

        safe_spawn = self._safe_spawn(*self.player.rect.center)
        self.player.controller.teleport(*safe_spawn)
        self.update_camera()

    # --------------------------------------
    # 碰撞
    # --------------------------------------

    def get_obstacles(self):
        raw = self.scene.map_manager.get_collisions()
        obstacles = []

        for item in raw:

            if isinstance(item, pygame.Rect):
                obstacles.append(item.copy())

            elif isinstance(item, (list, tuple)):
                if len(item) == 4:
                    obstacles.append(pygame.Rect(*item))

            elif isinstance(item, dict):

                if "rect" in item:
                    obstacles.append(
                        pygame.Rect(*item["rect"])
                    )

                elif all(
                    key in item
                    for key in ("x", "y", "width", "height")
                ):
                    obstacles.append(
                        pygame.Rect(
                            item["x"],
                            item["y"],
                            item["width"],
                            item["height"]
                        )
                    )

        return obstacles

    def _safe_spawn(self, x, y):
        """尋找附近可站立的出生點，避免傳送後陷在家具或牆壁。"""
        bounds = pygame.Rect(0, 0, self.scene.map_data["width"], self.scene.map_data["height"])
        obstacles = self.get_obstacles()
        base = pygame.Vector2(x, y)
        for radius in range(0, 385, 16):
            candidates = [(0, 0)] if radius == 0 else [
                (radius, 0), (-radius, 0), (0, radius), (0, -radius),
                (radius, radius), (-radius, radius), (radius, -radius), (-radius, -radius),
                (radius // 2, radius), (-radius // 2, radius),
            ]
            for dx, dy in candidates:
                test = self.player.rect.copy()
                test.center = (round(base.x + dx), round(base.y + dy))
                if bounds.contains(test) and not any(test.colliderect(o) for o in obstacles):
                    return test.center
        return (round(x), round(y))

    # --------------------------------------
    # 攝影機
    # --------------------------------------

    def update_camera(self):
        scene = self.scene

        self.scene.camera.follow(
            self.player.rect.centerx,
            self.player.rect.centery,
            scene.map_data["width"],
            scene.map_data["height"]
        )

    # --------------------------------------
    # 出口資料
    # --------------------------------------

    def get_exit_rect(self, exit_data):

        raw = exit_data.get("rect")

        if not isinstance(raw, (list, tuple)):
            return None

        if len(raw) != 4:
            return None

        return pygame.Rect(*raw)

    def is_player_near_exit(self, exit_data):
        """Single source of truth for keyboard and mouse door interactions.

        The player has a small foot collision box. The door's artwork is much
        taller than the threshold, so its interaction padding must not depend
        on being able to walk through the solid door/base collision.
        """
        exit_rect = self.get_exit_rect(exit_data)
        if exit_rect is None:
            return False
        padding = int(exit_data.get("interaction_padding", 76))
        padding = max(0, min(padding, 140))
        return self.player.rect.inflate(padding, padding).colliderect(exit_rect)

    def find_nearby_exit(self):

        player_rect = self.player.rect

        # Interaction must happen at the real entrance, never at a point
        # far along an invisible or solid wall next to its door picture.
        candidates = []
        for exit_data in self.scene.map_manager.get_exits():

            exit_rect = self.get_exit_rect(exit_data)
            if exit_rect is None:
                continue

            # Keyboard, visible marker and clickable prompt use the SAME range.
            if self.is_player_near_exit(exit_data):
                distance = pygame.Vector2(player_rect.center).distance_to(exit_rect.center)
                candidates.append((distance, exit_data))

        return min(candidates,key=lambda item:item[0])[1] if candidates else None

    def is_exit_unlocked(self, exit_data):

        condition = exit_data.get("unlock_condition")

        if not condition:
            return True

        # 預留任務系統接口
        quest_system = getattr(
            self.scene, "quest_system", None
        )

        if quest_system is None:
            return False

        if hasattr(quest_system, "is_completed"):
            return bool(
                quest_system.is_completed(condition)
            )

        return False

    # --------------------------------------
    # 訊息
    # --------------------------------------

    def show_message(self, message, duration=2.0):
        self.message = str(message)
        self.message_timer = duration

    # --------------------------------------
    # 地圖切換
    # --------------------------------------

    def transition(self, exit_id):

        scene = self.scene

        result = scene.map_manager.transition(exit_id)

        scene.map_id = result["map_id"]
        scene.map_data = scene.map_manager.current_map
        scene.spawn = result["spawn"]

        scene.map_loaded = False
        if hasattr(scene,'npc_shop'):
            scene.npc_shop._fade_cache.clear()
            scene.npc_shop._occluder_masks.clear()

        safe_spawn = self._safe_spawn(*scene.spawn)
        self.player.controller.teleport(*safe_spawn)
        scene.spawn = safe_spawn

        self.player.controller.direction = "down"

        self.player.animator.set_animation(
            "idle", "down"
        )

        self.transition_cooldown = 1.0

        self.fade_alpha = 210

        self.nearby_exit = None
        self._interaction_prompt_rect = None

        self.update_camera()

        self.show_message(
            f"已進入：{scene.map_data['name']}",
            2.5
        )

        print(
            "地圖切換成功：",
            scene.map_id,
            "出生點：",
            scene.spawn
        )

        return result

    # --------------------------------------
    # E 鍵互動
    # --------------------------------------

    def interact(self):
        """執行目前附近出口的互動。"""
        if self.transition_cooldown > 0:
            return True

        exit_data = self.find_nearby_exit()
        if exit_data is None:
            return False

        if not self.is_exit_unlocked(exit_data):
            condition = exit_data.get("unlock_condition", "未知條件")
            self.show_message(f"此傳送門尚未解鎖：{condition}")
            return True

        target = exit_data.get("target")
        target_file = self.scene.root / "data/maps" / f"{target}.json"

        if not target_file.is_file():
            self.show_message(f"目的地尚未開放：{target}")
            return True

        try:
            self.transition(exit_data["id"])
        except Exception as error:
            self.show_message(f"傳送失敗：{error}")
            print("地圖切換錯誤：", repr(error))

        return True

    # 獨立場景在主地圖的入口標記與用途提示。
    # 不繪製傳送門；標記只指示真正的場景入口。
    LOCATION_LABELS = {
        "library_portal": ("魔法圖書館（一樓）", "BOOK", "閱讀、探索隱藏書籍與劇情"),
        "classroom_portal": ("魔法教室（一樓）", "CLASS", "課程、調查魔法儀器與線索"),
        "to_entrance": ("學院入口", "OUT", "返回學院入口"),
        "to_hall": ("中央大廳", "HALL", "進入學院中央大廳"),
        "forest_portal": ("森林", "FOR", "探索學院周邊森林"),
        "shop_portal": ("商店", "SHOP", "商店"),
        "item_shop_portal": ("星露雜貨店", "SHOP", "購買冒險用品"),
        "weapon_shop_portal": ("赤鐵武器鋪", "GEAR", "購買武器裝備"),
    }

    def _location_rects(self):
        for exit_data in self.scene.map_manager.get_exits():
            rect = self.get_exit_rect(exit_data)
            if rect is None:
                continue
            label, symbol, description = self.LOCATION_LABELS.get(
                exit_data.get("id"), ("入口", "GO", "場景入口")
            )
            cx, cy = self.scene.camera.world_to_screen(*rect.center)
            marker = pygame.Rect(0, 0, 128, 43)
            marker.midbottom = (cx, cy - 28)
            yield exit_data, marker, label, symbol, description

    def draw_world_doors(self, screen):
        """MapRenderer draws the 2D PNG doors; never draw rectangle doors."""
        return

    def draw_collision_debug(self, screen):
        """F3 debug overlay: collision rectangles in camera coordinates."""
        return  # 正式版不顯示碰撞框
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for obstacle in self.get_obstacles():
            r = obstacle.move(-int(self.scene.camera.x), -int(self.scene.camera.y))
            if r.colliderect(screen.get_rect()):
                pygame.draw.rect(overlay, (245, 65, 65, 55), r)
                pygame.draw.rect(overlay, (255, 70, 70, 220), r, 2)
        screen.blit(overlay, (0, 0))

    def draw_location_markers(self, screen):
        mouse = pygame.mouse.get_pos()
        for exit_data, rect, label, symbol, description in self._location_rects():
            if exit_data.get("id") not in ("to_hall", "library_portal", "classroom_portal", "item_shop_portal", "weapon_shop_portal"):
                continue
            if not rect.colliderect(screen.get_rect()):
                continue
            exit_rect = self.get_exit_rect(exit_data)
            near = self.is_player_near_exit(exit_data)
            hovered = rect.collidepoint(mouse)
            if not near and not hovered:
                continue
            bg = (34, 37, 61)
            pygame.draw.rect(screen, bg, rect, border_radius=6)
            pygame.draw.rect(screen, (224, 184, 104), rect, 2, border_radius=6)
            font = self.scene.ctx.font_small
            name = font.render(label, True, (252, 230, 179))
            prompt = font.render("E / 點擊進入", True, (192, 218, 229))
            screen.blit(name, name.get_rect(centerx=rect.centerx, y=rect.y+3))
            screen.blit(prompt, prompt.get_rect(centerx=rect.centerx, y=rect.y+22))

    def click_location_marker(self, pos):
        for exit_data, rect, _, _, _ in self._location_rects():
            if not rect.collidepoint(pos):
                continue
            if self.transition_cooldown > 0:
                return True
            # Click and E now share the exact same distance check.
            if not self.is_player_near_exit(exit_data):
                self.show_message("請先靠近入口，再點擊標示或按 E")
                return True
            if not self.is_exit_unlocked(exit_data):
                self.show_message("此區域尚未解鎖")
                return True
            target = exit_data.get("target")
            if not (self.scene.root / "data/maps" / f"{target}.json").is_file():
                self.show_message("此區域尚未開放")
                return True
            try:
                self.transition(exit_data["id"])
            except Exception as error:
                self.show_message(f"切換失敗：{error}")
            return True
        return False

    def click_interaction_prompt(self, pos):
        """The on-screen E prompt is a real, clickable entrance button."""
        exit_data = self.find_nearby_exit()
        if exit_data is None:
            return False
        rect = self._interaction_prompt_rect
        if rect is None or not rect.collidepoint(pos):
            return False
        return self.interact()

    def handle_event(self, event):
        # 相容舊事件呼叫；主要鍵盤輸入由 GameScene 統一輪詢。
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            return self.interact()
        return False

    def update(self, dt):

        scene = self.scene

        dt = max(0.0, min(dt, 0.1))

        self.transition_cooldown = max(
            0.0,
            self.transition_cooldown - dt
        )

        self.fade_alpha = max(
            0,
            self.fade_alpha - 400 * dt
        )

        self.message_timer = max(
            0.0,
            self.message_timer - dt
        )

        if scene.player_menu.opened or getattr(scene, "npc_shop", None) and (scene.npc_shop.shop or scene.npc_shop.dialogue):

            self.player.controller.state = "idle"

            self.player.animator.set_animation(
                "idle",
                self.player.controller.direction
            )

            self.player.animator.update(dt)
            self.nearby_exit = None
            return

        npc_system = getattr(scene, 'npc_shop', None)
        obstacles = self.get_obstacles()
        if npc_system is not None:
            obstacles += npc_system.npc_obstacles()
        self.player.update(dt, obstacles=obstacles)

        # 地圖邊界
        rect = self.player.rect

        bounds = pygame.Rect(
            0, 0,
            scene.map_data["width"],
            scene.map_data["height"]
        )

        rect.clamp_ip(bounds)

        self.player.controller.position.update(
            rect.centerx,
            rect.centery
        )

        self.update_camera()

        # 更新附近出口
        self.nearby_exit = self.find_nearby_exit()

    # --------------------------------------
    # 繪製
    # --------------------------------------

    def draw(self, screen, include_player=True):

        scene = self.scene

        if include_player:
            self.player.draw(
                screen,
                camera_offset=(scene.camera.x, scene.camera.y)
            )

        # Hall portal artwork is now taken from real pixel-art assets and
        # rendered in the map depth pipeline (no Pygame rectangle doors).
        self.draw_location_markers(screen)

        # 出口互動提示（滑鼠也能點擊，避免瀏覽器未取得鍵盤焦點）。
        self._interaction_prompt_rect = None
        if self.nearby_exit is not None:

            unlocked = self.is_exit_unlocked(
                self.nearby_exit
            )

            destination = self.LOCATION_LABELS.get(
                self.nearby_exit.get('id'), ('場景入口', '', '')
            )[0]
            if not unlocked:
                label = "E  尚未解鎖"
            elif self.nearby_exit.get('id') == 'to_hall':
                label = "E / 點擊  進入中央大廳"
            elif self.nearby_exit.get('id') == 'to_entrance':
                label = "E  返回學院入口"
            else:
                label = "E  進入：" + destination

            font = scene.ctx.font_medium

            text = font.render(
                label,
                True,
                (255, 230, 170)
            )

            panel = pygame.Rect(
                0, 0,
                text.get_width() + 36,
                46
            )

            panel.center = (
                screen.get_width() // 2,
                screen.get_height() - 65
            )
            self._interaction_prompt_rect = panel.copy()
            hovering = panel.collidepoint(pygame.mouse.get_pos())

            pygame.draw.rect(
                screen,
                (75, 54, 100) if hovering else (25, 20, 45),
                panel,
                border_radius=10
            )

            pygame.draw.rect(
                screen,
                (225, 185, 100),
                panel,
                2,
                border_radius=10
            )

            screen.blit(
                text,
                text.get_rect(center=panel.center)
            )

        # 操作訊息
        if self.message_timer > 0:

            font = scene.ctx.font_small

            text = font.render(
                self.message,
                True,
                (255, 235, 190)
            )

            panel = text.get_rect(
                center=(
                    screen.get_width() // 2,
                    45
                )
            ).inflate(30, 18)

            pygame.draw.rect(
                screen,
                (25, 20, 45),
                panel,
                border_radius=8
            )

            screen.blit(
                text,
                text.get_rect(center=panel.center)
            )

        # 傳送後的淡入效果
        if self.fade_alpha > 0:

            overlay = pygame.Surface(
                screen.get_size(),
                pygame.SRCALPHA
            )

            overlay.fill((
                12, 8, 30,
                int(self.fade_alpha)
            ))

            screen.blit(overlay, (0, 0))
