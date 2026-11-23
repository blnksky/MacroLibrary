class Keyboard:
    def __init__(self, handler):
        self.handler = handler

    def press(self, key):
        return self.handler.press(key, device="keyboard")

    def hold(self, key):
        return self.handler.hold(key, device="keyboard")

    def release(self, key):
        return self.handler.release(key, device="keyboard")

    def is_pressed(self, key):
        return self.handler.is_pressed(key)

    def hook(self, callback):
        return self.handler.hook(callback, device="keyboard")

    def unhook(self, handle):
        return self.handler.unhook(handle)
