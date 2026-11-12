import pygame


class PlayerAnimator:
    def __init__(self, class_id="balanced_mage"):
        self.class_id = class_id
        self.state = "idle"
        self.direction = "down"
        self.frame_index = 0
        self.elapsed = 0.0
        self.animations = {}
        self.frame_duration = {
            "idle": 0.25,
            "walk": 0.12,
            "attack": 0.09,
            "cast": 0.12,
            "hurt": 0.15
        }

    def register(self, state, direction, frames):
        self.animations[(state, direction)] = frames

    def set_animation(self, state, direction):
        if (
            state != self.state
            or direction != self.direction
        ):
            self.state = state
            self.direction = direction
            self.frame_index = 0
            self.elapsed = 0.0

    def update(self, dt):
        frames = self.animations.get(
            (self.state, self.direction), []
        )
        if not frames:
            return

        self.elapsed += max(0, dt)
        duration = self.frame_duration.get(
            self.state, 0.15
        )

        while self.elapsed >= duration:
            self.elapsed -= duration
            self.frame_index = (
                self.frame_index + 1
            ) % len(frames)

    def get_frame(self):
        frames = self.animations.get(
            (self.state, self.direction), []
        )
        if not frames:
            return None
        return frames[self.frame_index % len(frames)]
