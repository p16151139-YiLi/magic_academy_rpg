import pygame


class PlayerController:
    def __init__(self, x=640, y=360):
        self.position = pygame.Vector2(x, y)
        self.speed = 260
        self.direction = "down"
        self.state = "idle"
        self.size = (24, 18)
        self.rect = pygame.Rect(0, 0, *self.size)
        self.rect.center = (round(x), round(y))
        self.enabled = True

    def update(self, dt, obstacles=None, keys=None):
        if not self.enabled:
            self.state = "idle"
            return

        if keys is None:
            keys = pygame.key.get_pressed()

        dx = (
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        )
        dy = (
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP])
        )

        movement = pygame.Vector2(dx, dy)

        if movement.length_squared() == 0:
            self.state = "idle"
            return

        movement.normalize_ip()
        self.state = "walk"

        if abs(movement.x) > abs(movement.y):
            self.direction = (
                "right" if movement.x > 0 else "left"
            )
        else:
            self.direction = (
                "down" if movement.y > 0 else "up"
            )

        obstacles = obstacles or []
        delta = movement * self.speed * max(0, min(dt, 0.1))

        # 每軸先求出最近的阻擋邊界，避免多個矩形反覆推動角色。
        for axis, amount in (("x", delta.x), ("y", delta.y)):
            if abs(amount) < 0.00001:
                continue
            old = self.rect.copy()
            target = self.position.x + amount if axis == "x" else self.position.y + amount
            proposed = old.copy()
            if axis == "x":
                proposed.centerx = round(target)
            else:
                proposed.centery = round(target)
            for obstacle in obstacles:
                if not isinstance(obstacle, pygame.Rect):
                    obstacle = pygame.Rect(obstacle)
                if axis == "x" and old.bottom > obstacle.top and old.top < obstacle.bottom:
                    if amount > 0 and old.right <= obstacle.left and proposed.right > obstacle.left:
                        target = min(target, obstacle.left - old.width / 2)
                    elif amount < 0 and old.left >= obstacle.right and proposed.left < obstacle.right:
                        target = max(target, obstacle.right + old.width / 2)
                if axis == "y" and old.right > obstacle.left and old.left < obstacle.right:
                    if amount > 0 and old.bottom <= obstacle.top and proposed.bottom > obstacle.top:
                        target = min(target, obstacle.top - old.height / 2)
                    elif amount < 0 and old.top >= obstacle.bottom and proposed.top < obstacle.bottom:
                        target = max(target, obstacle.bottom + old.height / 2)
            if axis == "x":
                self.position.x = target
            else:
                self.position.y = target
            self._sync_rect()

    def _sync_rect(self):
        self.rect.center = (
            round(self.position.x),
            round(self.position.y)
        )

    def teleport(self, x, y):
        self.position.update(x, y)
        self._sync_rect()
        self.state = "idle"
