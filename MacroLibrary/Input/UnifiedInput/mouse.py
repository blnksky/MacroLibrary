class Mouse:
    def __init__(self, handler):
        self.handler = handler

    def press(self, button):
        return self.handler.press(button, device="mouse")

    def hold(self, button):
        return self.handler.hold(button, device="mouse")

    def release(self, button):
        return self.handler.release(button, device="mouse")

    def is_pressed(self, button):
        return self.handler.is_pressed(button)

    def hook(self, callback):
        return self.handler.hook(callback, device="mouse")

    def unhook(self, handle):
        return self.handler.unhook(handle)
