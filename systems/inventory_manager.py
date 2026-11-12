import copy
import json
import os
from pathlib import Path
from systems.save_store import read_json as persistent_read, write_json as persistent_write

ROOT = Path(__file__).resolve().parents[1]


EQUIPMENT_SLOTS = ("weapon", "armor", "shoes", "ring", "medal")

class InventoryManager:
    def __init__(self):
        self.db_path = ROOT / "data/items/item_database.json"
        self.save_path = ROOT / "data/player/inventory.json"
        self.player_path = ROOT / "data/player/player_data.json"

        self.database = self._read_json(self.db_path, {})
        if isinstance(self.database, dict) and "items" in self.database:
            entries = self.database["items"]
            if isinstance(entries, list):
                self.database = {
                    item["id"]: item
                    for item in entries if "id" in item
                }

        self.data = self._read_json(self.save_path, {
            "capacity": 20,
            "items": [],
            "equipment": {"weapon": None, "armor": None}
        })
        self.data.setdefault("capacity", 20)
        self.data.setdefault("items", [])
        self.data.setdefault("equipment", {})
        self.data["equipment"].setdefault("weapon", None)
        self.data["equipment"].setdefault("armor", None)
        for extra_slot in EQUIPMENT_SLOTS:
            self.data["equipment"].setdefault(extra_slot, None)

        self.last_message = ""
        if not self.save_path.exists():
            self.save()

    @staticmethod
    def _read_json(path, default):
        return persistent_read(path, default)

    @staticmethod
    def _write_json(path, data):
        persistent_write(path, data)

    def save(self):
        self._write_json(self.save_path, self.data)

    def reload(self):
        self.data = self._read_json(self.save_path, self.data)
        self.data.setdefault("capacity", 20)
        self.data.setdefault("items", [])
        self.data.setdefault("equipment", {})
        self.data["equipment"].setdefault("weapon", None)
        self.data["equipment"].setdefault("armor", None)
        for extra_slot in EQUIPMENT_SLOTS:
            self.data["equipment"].setdefault(extra_slot, None)

    def _fail(self, message):
        self.last_message = message
        return False

    def _success(self, message):
        self.last_message = message
        return True

    def get_item_info(self, item_id):
        return self.database.get(item_id, {})

    def get_items(self, category="all"):
        if category in ("all", "全部", None):
            return list(self.data["items"])
        return [
            item for item in self.data["items"]
            if self.database.get(item["item_id"], {}).get("type")
            == category
        ]

    def get_item_count(self, item_id):
        return sum(
            int(item.get("amount", 0))
            for item in self.data["items"]
            if item.get("item_id") == item_id
        )

    def _stack_limit(self, item_id):
        info = self.get_item_info(item_id)
        if not info:
            return 0
        if info.get("stackable") is False:
            return 1
        if info.get("slot") in EQUIPMENT_SLOTS or info.get("type") in ("weapon", "armor", "equipment"):
            return max(1, int(info.get("max_stack", 1)))
        return max(1, int(info.get("max_stack", 99)))

    def _add_to(self, state, item_id, amount):
        if item_id not in self.database or amount <= 0:
            return False

        limit = self._stack_limit(item_id)
        remaining = amount

        for entry in state["items"]:
            if entry["item_id"] != item_id:
                continue
            free = max(0, limit - int(entry["amount"]))
            take = min(free, remaining)
            entry["amount"] += take
            remaining -= take
            if remaining == 0:
                return True

        capacity = int(state.get("capacity", 20))
        while remaining > 0:
            if len(state["items"]) >= capacity:
                return False
            take = min(limit, remaining)
            state["items"].append({
                "item_id": item_id,
                "amount": take
            })
            remaining -= take
        return True

    @staticmethod
    def _remove_from(state, item_id, amount):
        if amount <= 0:
            return False
        owned = sum(
            int(entry["amount"])
            for entry in state["items"]
            if entry["item_id"] == item_id
        )
        if owned < amount:
            return False

        remaining = amount
        for entry in list(state["items"]):
            if entry["item_id"] != item_id:
                continue
            take = min(int(entry["amount"]), remaining)
            entry["amount"] -= take
            remaining -= take
            if entry["amount"] <= 0:
                state["items"].remove(entry)
            if remaining == 0:
                break
        return True

    def add_item(self, item_id, amount=1):
        if item_id not in self.database:
            return self._fail("找不到此物品")
        if not isinstance(amount, int) or amount <= 0:
            return self._fail("物品數量不正確")

        staged = copy.deepcopy(self.data)
        if not self._add_to(staged, item_id, amount):
            return self._fail("背包空間不足")

        self._write_json(self.save_path, staged)
        self.data = staged
        return self._success("獲得物品")

    def remove_item(self, item_id, amount=1):
        if not isinstance(amount, int) or amount <= 0:
            return self._fail("物品數量不正確")

        staged = copy.deepcopy(self.data)
        if not self._remove_from(staged, item_id, amount):
            return self._fail("物品數量不足")

        self._write_json(self.save_path, staged)
        self.data = staged
        return self._success("移除物品")

    def use_item(self, item_id):
        info = self.get_item_info(item_id)
        if info.get("type") not in ("consumable", "potion"):
            return self._fail("這個物品無法使用")
        if self.get_item_count(item_id) < 1:
            return self._fail("沒有此物品")

        player = self._read_json(self.player_path, {})
        if not player:
            return self._fail("找不到角色資料")

        effects = info.get("effects", info.get("effect", {}))
        if not isinstance(effects, dict):
            return self._fail("物品效果資料不正確")

        updated = copy.deepcopy(player)
        changed = False

        for key, value in effects.items():
            normalized = str(key).lower()
            if normalized in ("hp", "heal_hp", "restore_hp"):
                resource = "hp"
            elif normalized in ("mp", "heal_mp", "restore_mp"):
                resource = "mp"
            else:
                continue

            maximum = int(updated.get("max_" + resource, 0))
            current = int(updated.get(resource, 0))
            gain = max(0, int(value))
            new_value = min(maximum, current + gain)
            if new_value > current:
                updated[resource] = new_value
                changed = True

        if not changed:
            return self._fail("目前不需要使用這個物品")

        staged = copy.deepcopy(self.data)
        self._remove_from(staged, item_id, 1)

        # 先寫角色資料，再寫背包；若第二次寫入失敗，
        # 嘗試還原角色資料，避免扣除物品卻沒有恢復效果。
        try:
            self._write_json(self.player_path, updated)
            self._write_json(self.save_path, staged)
        except Exception:
            self._write_json(self.player_path, player)
            raise

        self.data = staged
        return self._success("物品使用成功")

    def equip_item(self, item_id):
        info = self.get_item_info(item_id)
        slot = info.get("slot")
        if slot not in EQUIPMENT_SLOTS:
            return self._fail("此物品無法裝備")
        if self.get_item_count(item_id) < 1:
            return self._fail("背包中沒有此裝備")

        staged = copy.deepcopy(self.data)
        previous = staged["equipment"].get(slot)

        if not self._remove_from(staged, item_id, 1):
            return self._fail("裝備數量不足")

        if previous and not self._add_to(staged, previous, 1):
            return self._fail("背包空間不足，無法替換裝備")

        staged["equipment"][slot] = item_id
        self._write_json(self.save_path, staged)
        self.data = staged
        return self._success("裝備成功")

    def unequip_item(self, slot):
        if slot not in EQUIPMENT_SLOTS:
            return self._fail("裝備欄位不正確")

        item_id = self.data["equipment"].get(slot)
        if not item_id:
            return self._fail("此欄位沒有裝備")

        staged = copy.deepcopy(self.data)
        if not self._add_to(staged, item_id, 1):
            return self._fail("背包已滿，無法卸下裝備")

        staged["equipment"][slot] = None
        self._write_json(self.save_path, staged)
        self.data = staged
        return self._success("卸下裝備成功")

    def get_equipment_bonuses(self):
        bonuses = {}
        for item_id in self.data["equipment"].values():
            if not item_id:
                continue
            info = self.get_item_info(item_id)
            for key, value in info.get("bonuses", {}).items():
                bonuses[key] = bonuses.get(key, 0) + value
        return bonuses

    def get_equipped_item(self, slot):
        return self.data["equipment"].get(slot)

    def get_free_slots(self):
        return max(
            0,
            int(self.data["capacity"]) - len(self.data["items"])
        )

    def is_full(self):
        return self.get_free_slots() == 0

    def can_add_item(self, item_id, amount=1):
        if item_id not in self.database:
            return False
        if not isinstance(amount, int) or amount <= 0:
            return False
        staged = copy.deepcopy(self.data)
        return self._add_to(staged, item_id, amount)


# STAGE3_EQUIPMENT_STATS_SYNC

from systems.character_progression import (
    ensure as _stage3_ensure,
    read as _stage3_read,
    write as _stage3_write,
    synchronize as _stage3_synchronize,
    PLAYER as _stage3_player_path,
)

_stage3_original_equip = InventoryManager.equip_item
_stage3_original_unequip = InventoryManager.unequip_item


def _stage3_sync_equipment_stats():
    """裝備變更後，更新角色 HP/MP 上限與當前值。"""
    if not _stage3_player_path.exists():
        return

    data = _stage3_ensure(
        _stage3_read(_stage3_player_path, {})
    )

    old_max = (
        int(data.get("max_hp", 100)),
        int(data.get("max_mp", 50)),
    )

    _stage3_synchronize(data, old_max)
    _stage3_write(_stage3_player_path, data)


def _stage3_equip_item(self, item_id):
    success = _stage3_original_equip(self, item_id)

    if success:
        _stage3_sync_equipment_stats()

    return success


def _stage3_unequip_item(self, slot):
    success = _stage3_original_unequip(self, slot)

    if success:
        _stage3_sync_equipment_stats()

    return success


InventoryManager.equip_item = _stage3_equip_item
InventoryManager.unequip_item = _stage3_unequip_item
