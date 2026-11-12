class BaseScene:

    def __init__(self, ctx):
        self.ctx = ctx

    def draw(self):
        pass

    def handle_event(self, event):
        return None

    def update(self, dt):
        pass
