import pygame
import json
import asyncio

from settings import *

from scenes.scene_manager import SceneManager
from scenes.title_scene import TitleScene
from scenes.settings_scene import SettingsScene
from scenes.class_selection_scene import ClassSelectionScene
from scenes.credits_scene import CreditsScene
from scenes.game_scene import GameScene

from systems.audio_manager import AudioManager


# =========================================
# 初始化
# =========================================

pygame.init()

try:
    pygame.mixer.init()
except pygame.error:
    pass

pygame.display.set_caption(GAME_TITLE)

screen = pygame.display.set_mode(SCREEN_SIZE)
clock = pygame.time.Clock()


# =========================================
# 中文字型
# =========================================

def load_font(size):
    font_path = FONT_PATH if FONT_PATH.is_file() else None
    return pygame.font.Font(str(font_path) if font_path else None, size)


font_small = load_font(20)
font_medium = load_font(28)
font_large = load_font(42)


# =========================================
# 讀取設定
# =========================================

default_settings = {
    "music_volume": DEFAULT_MUSIC_VOLUME,
    "sfx_volume": DEFAULT_SFX_VOLUME,
    "fullscreen": DEFAULT_FULLSCREEN
}

if USER_SETTINGS_PATH.exists():

    try:
        saved = json.loads(
            USER_SETTINGS_PATH.read_text(encoding="utf-8")
        )

        default_settings.update(saved)

    except (json.JSONDecodeError, OSError):
        pass


music_volume = max(
    0.0,
    min(1.0, float(default_settings["music_volume"]))
)

sfx_volume = max(
    0.0,
    min(1.0, float(default_settings["sfx_volume"]))
)

fullscreen = bool(default_settings["fullscreen"])


# =========================================
# 讀取職業資料
# =========================================

with open(CLASS_DATA_PATH, "r", encoding="utf-8") as f:
    raw_classes = json.load(f)

classes = []

for class_id, info in raw_classes.items():

    item = dict(info)
    item["id"] = class_id

    classes.append(item)


# =========================================
# 封面圖片
# =========================================

title_background = None

if TITLE_IMAGE.exists():

    try:

        image = pygame.image.load(
            str(TITLE_IMAGE)
        ).convert_alpha()

        title_background = pygame.transform.smoothscale(
            image,
            SCREEN_SIZE
        )

    except pygame.error as error:
        print("封面圖片載入失敗：", error)


# =========================================
# 共用繪圖函式
# =========================================

def draw_text(text, font, color, x, y, center=True):

    surface = font.render(str(text), True, color)

    rect = surface.get_rect()

    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    screen.blit(surface, rect)


def draw_panel(rect):

    panel = pygame.Surface(
        rect.size,
        pygame.SRCALPHA
    )

    panel.fill((20, 17, 45, 235))

    screen.blit(panel, rect.topleft)

    pygame.draw.rect(
        screen,
        COLORS["gold"],
        rect,
        2,
        border_radius=12
    )


def draw_button(rect, text, mouse_pos):

    hovered = rect.collidepoint(mouse_pos)

    color = (
        (100, 75, 145)
        if hovered
        else (45, 38, 85)
    )

    pygame.draw.rect(
        screen,
        color,
        rect,
        border_radius=10
    )

    pygame.draw.rect(
        screen,
        COLORS["gold"],
        rect,
        2,
        border_radius=10
    )

    draw_text(
        text,
        font_medium,
        COLORS["white"],
        rect.centerx,
        rect.centery
    )


# =========================================
# 音效管理
# =========================================

audio = AudioManager(
    music_volume,
    sfx_volume
)


# =========================================
# 共用遊戲資料
# =========================================

class Context:
    pass


ctx = Context()

ctx.screen = screen
ctx.colors = COLORS
ctx.game_title = GAME_TITLE

ctx.font_small = font_small
ctx.font_medium = font_medium
ctx.font_large = font_large

ctx.title_background = title_background

ctx.classes = classes
ctx.selected_class = 0
ctx.selected_character_class = classes[0]

ctx.music_volume = music_volume
ctx.sfx_volume = sfx_volume
ctx.fullscreen = fullscreen

ctx.audio = audio


# =========================================
# 綁定共用繪圖函式
# 修正原始程式缺少的函式綁定
# =========================================

ctx.draw_text = draw_text
ctx.draw_panel = draw_panel
ctx.draw_button = draw_button


# =========================================
# 共用設定儲存
# =========================================

def save_settings():

    data = {
        "music_volume": ctx.music_volume,
        "sfx_volume": ctx.sfx_volume,
        "fullscreen": ctx.fullscreen
    }

    try:
        USER_SETTINGS_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        USER_SETTINGS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=4),
            encoding="utf-8"
        )

    except OSError as error:
        # 瀏覽器環境可能不允許寫入本機檔案
        print("設定儲存失敗：", error)


ctx.save_settings = save_settings



# =========================================
# 全螢幕功能已停用
# =========================================

def change_fullscreen(*args, **kwargs):
    return None

ctx.change_fullscreen = change_fullscreen
ctx.fullscreen = False

# =========================================
# 場景管理
# =========================================

scene_manager = SceneManager()

scene_manager.register("title", TitleScene(ctx))
scene_manager.register("settings", SettingsScene(ctx))
scene_manager.register("class_selection", ClassSelectionScene(ctx))
scene_manager.register("credits", CreditsScene(ctx))
scene_manager.register("game", GameScene(ctx))

scene_manager.switch("title")


# =========================================
# 非同步主迴圈
# =========================================

async def main():

    running = True

    while running:

        dt = 1.0 / FPS

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False
                break

            # Route all keys and clicks to the active scene. An Escape handled
            # globally would bypass panel-specific close and save actions.
            result = scene_manager.handle_event(event)

            if result == "quit":
                running = False
                break

            elif result is not None:

                if result == "game":

                    # 職業確認後重新建立遊戲場景
                    # 讓 PlayerWorldBridge 讀取最新職業
                    new_game_scene = GameScene(ctx)

                    scene_manager.register(
                        "game",
                        new_game_scene
                    )

                    print(
                        "遊戲場景重新建立完成：",
                        ctx.selected_class_id
                    )

                scene_manager.switch(result)

        if not running:
            break

        scene_manager.update(dt)

        # 確保場景使用最新的畫面物件
        ctx.screen = screen

        scene_manager.draw()

        pygame.display.flip()

        # 讓出瀏覽器執行權
        await asyncio.sleep(1.0 / FPS)

    save_settings()
    pygame.quit()


# =========================================
# 啟動
# =========================================

asyncio.run(main())
