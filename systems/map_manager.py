
import json
from pathlib import Path


class MapManager:

    def __init__(self, root_path):
        self.root = Path(root_path)
        self.maps_dir = self.root / "data/maps"
        self.current_map = None
        self.current_map_id = None

    def load_map(self, map_id):
        """讀取地圖資料。"""

        if not isinstance(map_id, str):
            raise TypeError("地圖 ID 必須是字串")

        if not map_id or not all(
            c.isascii() and (c.isalnum() or c == "_")
            for c in map_id
        ):
            raise ValueError("地圖 ID 格式不正確")

        path = self.maps_dir / f"{map_id}.json"

        if not path.is_file():
            raise FileNotFoundError(
                f"找不到地圖：{map_id}"
            )

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.validate_map(data, map_id)

        self.current_map = data
        self.current_map_id = map_id

        return data

    def validate_map(self, data, map_id):
        """檢查地圖基本資料格式。"""

        if not isinstance(data, dict):
            raise ValueError("地圖資料格式不正確")

        if data.get("id") != map_id:
            raise ValueError("地圖 ID 不一致")

        for field in ("width", "height", "tile_size"):
            value = data.get(field)

            if type(value) is not int or value <= 0:
                raise ValueError(
                    f"{field} 必須是正整數"
                )

        if not isinstance(data.get("spawn_points"), dict):
            raise ValueError("出生點資料格式不正確")

        for field in (
            "exits",
            "collision_rects",
            "objects",
            "npcs",
            "enemies"
        ):
            if not isinstance(data.get(field), list):
                raise ValueError(
                    f"{field} 必須是清單"
                )

    def get_spawn(self, spawn_id="default"):
        """取得出生點。"""

        if self.current_map is None:
            raise RuntimeError("尚未載入地圖")

        points = self.current_map["spawn_points"]

        if spawn_id not in points:
            raise KeyError(
                f"找不到出生點：{spawn_id}"
            )

        return tuple(points[spawn_id])

    def get_size(self):
        """取得地圖尺寸。"""

        if self.current_map is None:
            raise RuntimeError("尚未載入地圖")

        return (
            self.current_map["width"],
            self.current_map["height"]
        )

    def get_exits(self):
        if self.current_map is None:
            return []
        return self.current_map["exits"]

    def get_collisions(self):
        if self.current_map is None:
            return []
        return self.current_map["collision_rects"]

    def get_objects(self):
        if self.current_map is None:
            return []
        return self.current_map["objects"]

    def get_npcs(self):
        if self.current_map is None:
            return []
        return self.current_map["npcs"]

    def get_enemies(self):
        if self.current_map is None:
            return []
        return self.current_map["enemies"]

    def find_exit(self, exit_id):
        """尋找指定出口。"""

        for exit_data in self.get_exits():
            if exit_data.get("id") == exit_id:
                return exit_data

        return None

    def transition(self, exit_id):
        """切換地圖並取得新出生點。"""

        exit_data = self.find_exit(exit_id)

        if exit_data is None:
            raise KeyError(
                f"找不到出口：{exit_id}"
            )

        previous_map = self.current_map
        previous_id = self.current_map_id

        try:
            target = exit_data["target"]
            spawn_id = exit_data.get(
                "target_spawn", "default"
            )

            self.load_map(target)
            spawn = self.get_spawn(spawn_id)

        except Exception:
            self.current_map = previous_map
            self.current_map_id = previous_id
            raise

        return {
            "map_id": self.current_map_id,
            "spawn": spawn
        }
