class SceneManager:

    def __init__(self):
        self.scenes = {}
        self.current_scene_name = None

    def register(self, name, scene):
        self.scenes[name] = scene

    def switch(self, name):
        if name not in self.scenes:
            raise ValueError(f"找不到場景：{name}")

        self.current_scene_name = name

    @property
    def current_scene(self):
        if self.current_scene_name is None:
            return None

        return self.scenes[self.current_scene_name]

    def handle_event(self, event):
        if self.current_scene:
            return self.current_scene.handle_event(event)

        return None

    def update(self, dt):
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self):
        if self.current_scene:
            self.current_scene.draw()
