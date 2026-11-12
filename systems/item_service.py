
import json
from pathlib import Path

from systems.inventory_manager import InventoryManager
from systems.save_store import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


class ItemService:
    def __init__(self, inventory=None):
        self.inventory = inventory or InventoryManager()
        self.player_path = (
            ROOT / "data/player/player_data.json"
        )

    def get_player(self):
        return read_json(self.player_path, {})

    def refresh(self):
        self.inventory.reload()
        return self.get_snapshot()

    def get_snapshot(self):
        return {
            "player": self.get_player(),
            "inventory": self.inventory.data,
            "equipment_bonuses":
                self.inventory.get_equipment_bonuses()
        }

    def give_item(self, item_id, amount=1):
        success = self.inventory.add_item(
            item_id, amount
        )
        return self.result(success)

    def take_item(self, item_id, amount=1):
        success = self.inventory.remove_item(
            item_id, amount
        )
        return self.result(success)

    def use_item(self, item_id):
        success = self.inventory.use_item(item_id)
        return self.result(success)

    def equip_item(self, item_id):
        success = self.inventory.equip_item(item_id)
        return self.result(success)

    def unequip_item(self, slot):
        success = self.inventory.unequip_item(slot)
        return self.result(success)

    def result(self, success):
        return {
            "success": bool(success),
            "message": self.inventory.last_message,
            "snapshot": self.get_snapshot()
        }

    def get_item_count(self, item_id):
        return self.inventory.get_item_count(item_id)

    def get_equipment_bonuses(self):
        return self.inventory.get_equipment_bonuses()

    def grant_starting_gold_once(self):
        """One-time migration from Phase 8's memory-only coins to the real player save."""
        player = self.get_player()
        if not player.get('phase8_wallet_initialized', False):
            player['gold'] = max(0, int(player.get('gold', 0))) + 500
            player['phase8_wallet_initialized'] = True
            write_json(self.player_path, player)
        return int(player.get('gold', 0))

    def buy_item(self, item_id, price):
        """All-or-nothing purchase; respects inventory capacity and real wallet."""
        price = int(price)
        self.inventory.reload()
        player = self.get_player()
        gold = int(player.get('gold', 0))
        if item_id not in self.inventory.database or price < 0:
            return {'success': False, 'message': '商品資料錯誤'}
        if gold < price:
            return {'success': False, 'message': '金幣不足'}
        if not self.inventory.can_add_item(item_id, 1):
            return {'success': False, 'message': '背包已滿'}
        import copy
        before = copy.deepcopy(self.inventory.data)
        after = copy.deepcopy(before)
        if not self.inventory._add_to(after, item_id, 1):
            return {'success': False, 'message': '背包已滿'}
        updated = copy.deepcopy(player)
        updated['gold'] = gold - price
        try:
            self.inventory._write_json(self.inventory.save_path, after)
            try:
                write_json(self.player_path, updated)
            except Exception:
                self.inventory._write_json(self.inventory.save_path, before)
                raise
        except Exception as exc:
            return {'success': False, 'message': '儲存失敗，未完成購買'}
        self.inventory.data = after
        return {'success': True, 'message': '購買成功：' + self.inventory.database[item_id]['name'],
                'gold': updated['gold'], 'count': self.inventory.get_item_count(item_id)}
