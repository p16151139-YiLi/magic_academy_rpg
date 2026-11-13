
import pygame
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CharacterPortraitManager:

    def __init__(self):
        index_path = ROOT / "data/player/class_portraits.json"

        with open(index_path, encoding="utf-8") as f:
            self.portraits = json.load(f)

        self.cache = {}

    def get_portrait(self, job_id, size=(192, 192)):
        if job_id not in self.portraits:
            job_id = "balanced_mage"

        key = (job_id, tuple(size))

        if key not in self.cache:
            path = ROOT / self.portraits[job_id]["portrait"]

            image = pygame.image.load(str(path)).convert_alpha()

            image = pygame.transform.scale(
                image,
                size
            )

            self.cache[key] = image

        return self.cache[key]

    def draw(self, screen, job_id, x, y, size=(192, 192)):
        image = self.get_portrait(job_id, size)
        screen.blit(image, (int(x), int(y)))
