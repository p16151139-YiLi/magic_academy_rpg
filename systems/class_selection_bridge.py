from systems.player_class_manager import PlayerClassManager


class ClassSelectionBridge:

    def __init__(self):
        self.manager = PlayerClassManager()

    def select_class(self, class_id):
        """套用職業並儲存玩家資料。"""

        player_data = self.manager.apply_class(class_id)

        if player_data.get("class_id") != class_id:
            raise RuntimeError("職業資料寫入不一致")

        return player_data
