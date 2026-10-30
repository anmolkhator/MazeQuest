"""Small pygame widgets: Button and TextInput."""
import pygame
from .config import C


class Button:
    def __init__(self, rect, label, cb, color=None, show=None):
        self.rect, self.label, self.cb, self.color = pygame.Rect(rect), label, cb, color
        self.show = show or (lambda: True)

    def draw(self, scr, font):
        if not self.show():
            return
        bg = self.color or C["panel"]
        light = self.color and (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) > 170
        fg = C["white"] if self.color and not light else C["ink"]
        pygame.draw.rect(scr, bg, self.rect, border_radius=8)
        if not self.color:
            pygame.draw.rect(scr, C["line"], self.rect, 1, border_radius=8)
        txt = font.render(self.label() if callable(self.label) else self.label, True, fg)
        scr.blit(txt, txt.get_rect(center=self.rect.center))

    def click(self, pos):
        if self.show() and self.rect.collidepoint(pos):
            self.cb()
            return True
        return False


class TextInput:
    def __init__(self, rect, hint, secret=False, maxlen=16, upper=False):
        self.rect, self.hint, self.secret, self.maxlen, self.upper = pygame.Rect(rect), hint, secret, maxlen, upper
        self.text, self.active = "", False

    def key(self, e):
        if e.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif e.unicode and e.unicode.isprintable() and len(self.text) < self.maxlen:
            self.text += e.unicode.upper() if self.upper else e.unicode

    def draw(self, scr, font):
        pygame.draw.rect(scr, C["panel"], self.rect, border_radius=6)
        pygame.draw.rect(scr, C["path"] if self.active else C["line"], self.rect, 2, border_radius=6)
        shown = "*" * len(self.text) if self.secret else self.text
        txt = font.render(shown or self.hint, True, C["ink"] if shown else C["mute"])
        scr.blit(txt, (self.rect.x + 10, self.rect.centery - txt.get_height() // 2))
