import pygame
from pathlib import Path


class AudioManager:

    def __init__(self, music_volume=0.5, sfx_volume=0.7):
        self.music_volume = float(music_volume)
        self.sfx_volume = float(sfx_volume)
        self.sounds = {}

        self.apply_music_volume()

    def set_music_volume(self, value):
        self.music_volume = max(0.0, min(1.0, float(value)))
        self.apply_music_volume()

    def set_sfx_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, float(value)))

        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)

    def apply_music_volume(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.music_volume)
        except pygame.error:
            pass

    def play_music(self, path, loops=-1):
        path = Path(path)

        if not path.exists():
            return False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops)

            return True

        except (pygame.error, OSError):
            return False

    def play_sfx(self, path):
        path = Path(path)

        if not path.exists():
            return False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            key = str(path)

            if key not in self.sounds:
                self.sounds[key] = pygame.mixer.Sound(key)
                self.sounds[key].set_volume(self.sfx_volume)

            self.sounds[key].play()

            return True

        except (pygame.error, OSError):
            return False
