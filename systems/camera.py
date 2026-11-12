
class Camera:
    """負責將世界座標轉換為螢幕座標。"""

    def __init__(self, screen_width=1280, screen_height=720):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = 0
        self.y = 0

    def follow(self, target_x, target_y, map_width, map_height):
        """讓攝影機以指定座標為中心，並限制在地圖範圍內。"""

        desired_x = int(target_x - self.screen_width / 2)
        desired_y = int(target_y - self.screen_height / 2)

        self.x = max(
            0,
            min(desired_x, max(0, map_width - self.screen_width))
        )

        self.y = max(
            0,
            min(desired_y, max(0, map_height - self.screen_height))
        )

    def apply(self, rect):
        """取得物件在螢幕上的矩形。"""
        return rect.move(-self.x, -self.y)

    def world_to_screen(self, x, y):
        return int(x - self.x), int(y - self.y)

    def screen_to_world(self, x, y):
        return int(x + self.x), int(y + self.y)
