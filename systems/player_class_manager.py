import json
from pathlib import Path

from systems.character_progression import (
    PLAYER,
    defaults,
    ensure,
    synchronize,
    write,
    read,
)


ROOT = Path(__file__).resolve().parents[1]


class PlayerClassManager:
    """職業資料的唯一寫入入口，並保留既有自由配點資料。"""

    def __init__(self):
        self.class_path = ROOT / "data/player/mage_classes.json"
        self.player_path = PLAYER
        self.classes = json.loads(
            self.class_path.read_text(encoding="utf-8")
        )

    def apply_class(self, class_id):
        if class_id not in self.classes:
            raise ValueError(f"未知職業：{class_id}")

        job = self.classes[class_id]
        old_data = {}
        if self.player_path.exists():
            old_data = read(self.player_path, {})

        player = dict(old_data)
        player.setdefault("name", "見習冒險者")
        player.setdefault("level", 1)
        player.setdefault("exp", 0)
        player.setdefault("exp_to_next_level", 100)
        player.setdefault("gold", 0)

        player.update({
            "class_id": class_id,
            "class_name": job["name"],
            "hp": job["hp"],
            "max_hp": job["hp"],
            "mp": job["mp"],
            "max_mp": job["mp"],
        })

        attributes = dict(player.get("attributes", {}))
        attributes.update({
            "attack": job["attack"],
            "defense": job["defense"],
        })
        player["attributes"] = attributes

        # 已經自由配點的角色換職業時保留配點；
        # 尚未配點時使用新職業的初始能力值。
        old_progress = ensure(old_data) if old_data else None
        if old_progress and old_progress.get("allocated_points", 0) > 0:
            for key in (
                "base_stats", "unspent_points",
                "allocated_points", "hidden_talents"
            ):
                player[key] = old_progress[key]
        else:
            player["base_stats"] = defaults(class_id)
            player["unspent_points"] = 0
            player["allocated_points"] = 0

        player = ensure(player)
        player = synchronize(player)
        write(self.player_path, player)
        return player
