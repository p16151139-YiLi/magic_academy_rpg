import pygame

from systems.player_animator import PlayerAnimator
from systems.player_controller import PlayerController
from systems.player_sprite_loader import PlayerSpriteLoader


class PlayerEntity:
    def __init__(self, x=640, y=360, class_id="balanced_mage"):
        self.controller = PlayerController(x, y)
        self.animator = PlayerAnimator(class_id)
        self.class_id = class_id
        self.sprite_load_result = {"loaded": [], "missing": []}

        if pygame.display.get_surface() is not None:
            self.load_sprites()

    @property
    def rect(self):
        return self.controller.rect

    def load_sprites(self):
        self.sprite_load_result = PlayerSpriteLoader().load_into(self.animator)
        return self.sprite_load_result

    def update(self, dt, obstacles=None, keys=None):
        self.controller.update(dt, obstacles, keys)
        self.animator.set_animation(
            self.controller.state,
            self.controller.direction
        )
        self.animator.update(dt)

    def draw(self, surface, camera_offset=(0, 0)):
        ox, oy = camera_offset
        destination = self.rect.move(-ox, -oy)
        frame = self.animator.get_frame()

        if frame is None:
            pygame.draw.rect(
                surface, (100, 165, 235), destination,
                border_radius=5
            )
            return

        # 圖像與腳部碰撞盒分離；縮放不改變碰撞判定。
        frame = pygame.transform.scale(frame, (96, 96))
        image_rect = frame.get_rect(midbottom=(destination.centerx, destination.bottom + 7))
        surface.blit(frame, image_rect)
