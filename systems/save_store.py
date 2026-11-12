"""Persistent save adapter. Browser (Pygbag) -> localStorage, desktop -> JSON files.
The original JSON defaults remain in the packaged game. No secrets/network required.
"""
import json
import os
import copy
from pathlib import Path

PREFIX = 'magic_academy_phase8_v2:'


def _storage():
    try:
        import platform
        win = getattr(platform, 'window', None)
        if win is not None:
            return getattr(win, 'localStorage', None)
    except Exception:
        pass
    try:
        import js
        return js.window.localStorage
    except Exception:
        return None


def _key(path):
    path = Path(path)
    return PREFIX + path.as_posix().split('/data/')[-1]


def read_json(path, default=None):
    path = Path(path)
    storage = _storage()
    if storage is not None and '/data/' in path.as_posix():
        try:
            saved = storage.getItem(_key(path))
            if saved is not None and str(saved) not in ('null', 'undefined', 'None', ''):
                return json.loads(str(saved))
        except Exception as ex:
            print('localStorage read failed', type(ex).__name__)
    try:
        with path.open(encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return copy.deepcopy(default)


def write_json(path, data):
    path = Path(path)
    dumped = json.dumps(data, ensure_ascii=False, indent=2)
    saved_browser = False
    storage = _storage()
    if storage is not None and '/data/' in path.as_posix():
        try:
            storage.setItem(_key(path), dumped)
            saved_browser = True
        except Exception as ex:
            print('localStorage write failed', type(ex).__name__)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + '.tmp')
        temp.write_text(dumped, encoding='utf-8')
        os.replace(temp, path)
        return
    except OSError:
        if not saved_browser:
            raise
