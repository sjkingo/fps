import math
from pyglet import resource
from pyglet.window import key, mouse
import pyglet
import random
import sys

resource.path = ['fps/resources']
resource.reindex()

WINDOW_WIDTH = 0
WINDOW_HEIGHT = 0

def wrap(value, limit):
    if value > limit:
        value -= limit
    if value < 0:
        value += limit
    return value

class Sprite(pyglet.sprite.Sprite):
    pass

class MovingSprite(Sprite):
    dx = 0
    dy = 0
    rotation_speed = 0

    def __init__(self, img, x, y):
        self.radius = int(img.width / 2)
        self.linked_sprites = []
        super().__init__(img, x, y)
    
    def update(self, dt):
        x = int(self.x + self.dx * dt)
        y = int(self.y + self.dy * dt)
        self.x = wrap(x, WINDOW_WIDTH)
        self.y = wrap(y, WINDOW_HEIGHT)

        for sprite in self.linked_sprites:
            sprite.x = self.x + self.radius
            sprite.y = self.y + self.radius

    def draw(self):
        super().draw()
        for sprite in self.linked_sprites:
            sprite.draw()

    def collision_cells(self):
        current_x = int(self.x)
        current_y = int(self.y)
        for y in range(current_y - self.radius, current_y + self.radius + 1):
            for x in range(current_x - self.radius, current_x + self.radius + 1):
                yield (x, y)

class DebugInfoSprite:
    _debug_label = None

    def update_debug_label(self):
        if self._debug_label:
            self._debug_label.text = self.debug_text
        else:
            self._debug_label = pyglet.text.Label(text=self.debug_text, 
                    x=self.x, y=self.y, multiline=True, width=500)
            self.linked_sprites.append(self._debug_label)

class Asteroid(MovingSprite, DebugInfoSprite):
    MAX_ROTATION_SPEED = 20.0

    def __init__(self, img, x, y):
        super().__init__(img, x, y)
        self.dx = (random.random() - 0.5) * 25
        self.dy = (random.random() - 0.5) * 25
        self.rotation = random.random() * 360.0
        self.rotation_speed = random.random() * self.MAX_ROTATION_SPEED

    @property
    def debug_text(self):
        s = self.__class__.__name__ + '\n'
        s += f'({self.x}, {self.y})\n'
        s += f'dx={int(self.dx)} dy={int(self.dy)}\n'
        s += f'r={self.rotation}\n'
        return s

class StarImage:
    def __init__(self, img, x, y):
        self.img = img
        self.x = x
        self.y = y
        self.dx = 10
        self.has_left = False

    def update(self, dt):
        self.x += self.dx * dt

    def draw(self):
        self.img.blit(self.x, self.y)

class StarImageField:
    imgs = []

    def __init__(self, img):
        self.base_img = img
        self.new(0, 0)

    def new(self, x, y):
        i = StarImage(self.base_img, x, y)
        self.imgs.append(i)

    def update(self, dt):
        for i in list(self.imgs):
            i.update(dt)
            if i.x > 0 and not i.has_left:
                self.new(-self.base_img.width + 100, i.y)
                i.has_left = True
            if i.has_left and i.x > self.base_img.width:
                self.imgs.remove(i)

    def draw(self):
        for i in self.imgs:
            i.draw()

class Ship(MovingSprite, DebugInfoSprite):
    ROTATION_SPEED = 180.0

    def __init__(self, img):
        # centre anchor
        img.anchor_x = img.width //2
        img.anchor_y = img.height // 2

        initial_x = WINDOW_WIDTH // 2
        initial_y = WINDOW_HEIGHT // 2

        self.key_handler = key.KeyStateHandler()
        
        super().__init__(img, initial_x, initial_y)

    def update(self, dt):
        if self.key_handler[key.LEFT]:
            self.rotation -= self.ROTATION_SPEED * dt
        if self.key_handler[key.RIGHT]:
            self.rotation += self.ROTATION_SPEED * dt

        angle_radians = -math.radians(self.rotation)
        force_x = -math.sin(angle_radians) * 200.0 * dt
        force_y = math.cos(angle_radians) * 200.0 * dt

        if self.key_handler[key.UP]:
            self.dx += force_x
            self.dy += force_y

        if self._debug_label:
            self.update_debug_label()

        super().update(dt)

    @property
    def debug_text(self):
        s = self.__class__.__name__ + '\n'
        s += f'({self.x}, {self.y})\n'
        s += f'dx={self.dx} dy={self.dy} r={self.rotation}\n'
        return s

class Game(pyglet.window.Window):
    sprites = []

    def __init__(self, *args, **kwargs):
        num_asteroids = kwargs.pop('asteroids', 10)
        self.debug = kwargs.pop('debug', False)

        # super() must be called before setting dimmensions
        super().__init__(*args, **kwargs)

        global WINDOW_WIDTH, WINDOW_HEIGHT
        WINDOW_WIDTH = self.width
        WINDOW_HEIGHT = self.height

        # HUD
        self.fps = pyglet.window.FPSDisplay(self)
        self.fps.label = pyglet.text.Label(y=WINDOW_HEIGHT-20)

        # set up sprites
        self.sprites.append(Sprite(resource.image('white.png'), 0, 0))
        self.sprites.append(StarImageField(resource.image('star.jpg')))
        self.sprites.extend(self.get_asteroids(num_asteroids))

        # player ship
        self.ship = Ship(resource.image('ship.png'))
        self.push_handlers(self.ship.key_handler)
        self.sprites.append(self.ship)

        pyglet.clock.schedule_interval(self.update, 1/60.0)

    def on_draw(self):
        self.clear()
        self.fps.draw()

        for sprite in self.sprites:
            sprite.draw()
            if self.debug and hasattr(sprite, 'update_debug_label'):
                sprite.update_debug_label()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            sys.exit()
        return pyglet.event.EVENT_HANDLED

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            obj = self.check_collisions().get(x+y, None)
            if obj:
                obj.update_debug_label()

    def update(self, dt):
        for sprite in self.sprites:
            if hasattr(sprite, 'update'):
                sprite.update(dt)

    def get_asteroids(self, num):
        grid = pyglet.image.ImageGrid(resource.image('asteroids.png'), 8, 8)
        asteroids = []
        for i in range(num):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            index = (random.randint(0, 7), random.randint(0, 7))
            asteroid = Asteroid(img=grid[index], x=x, y=y)
            asteroid.rotation = random.randint(0, 360)
            asteroids.append(asteroid)
        return asteroids

    def check_collisions(self):
        hits = {}
        for sprite in self.sprites:
            if hasattr(sprite, 'collision_cells'):
                for x, y in sprite.collision_cells():
                    hits[x+y] = sprite
        return hits

def main():
    window = Game(
        fullscreen=True,
        caption='Asteroids',
        debug=True,
    )
    pyglet.app.run()
