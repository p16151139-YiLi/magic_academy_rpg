from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

GAME_TITLE = "Magic Academy: The Lost Ancient Magic"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

FPS = 60

DEFAULT_FULLSCREEN = False
DEFAULT_MUSIC_VOLUME = 0.5
DEFAULT_SFX_VOLUME = 0.7

COLORS = {
    "background": (15, 13, 35),
    "panel": (28, 24, 57),
    "gold": (235, 190, 95),
    "purple": (105, 75, 160),
    "blue": (55, 95, 175),
    "white": (245, 240, 255),
    "gray": (155, 155, 175),
    "green": (150, 205, 170),
}

ASSET_DIR = BASE_DIR / "assets"

TITLE_IMAGE = ASSET_DIR / "ui" / "menu" / "title_screen.png"

FONT_PATH = ASSET_DIR / "fonts" / "NotoSansTC-Regular.ttf"

CLASS_DATA_PATH = BASE_DIR / "data" / "class_data.json"

USER_SETTINGS_PATH = BASE_DIR / "data" / "user_settings.json"
