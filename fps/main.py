import math
from pyglet import resource
from pyglet.window import key, mouse
import pyglet
import random
import sys
import time

resource.path = ['fps/resources']
resource.reindex()

WINDOW_WIDTH = 0
WINDOW_HEIGHT = 0

class SpriteException(Exception):
    def __init__(self, obj):
        self.obj = obj

class SpriteOutOfBounds(SpriteException):
    pass

class DeleteSprite(SpriteException):
    pass

class CollisionBetween(Exception):
    def __init__(self, sprites, cell_pos):
        self.sprites = sprites
        self.cell_pos = cell_pos
        self.message = f'Collision between {sprites} at cell {cell_pos}'

class LinkedSprite:
    """
    Allows a sprite to have other sprites linked to it, where (x, y) movement
    is cascaded. This allows sprites to move as a group.
    """

    linked_sprites = None

    def __init__(self, *args, **kwargs):
        self.linked_sprites = []
        super().__init__(*args, **kwargs)

    def link(self, sprite):
        self.linked_sprites.append(sprite)

    def update(self, dt):
        for sprite in self.linked_sprites:
            sprite.x = self.x + self.radius
            sprite.y = self.y + self.radius
    
    def draw(self):
        for sprite in self.linked_sprites:
            sprite.draw()
        super().draw()

    def delete(self):
        for sprite in self.linked_sprites:
            self.linked_sprites.remove(sprite)
            sprite.delete()

class BaseSprite(LinkedSprite, pyglet.sprite.Sprite):
    """
    Provides a base class for sprites.
    """

    debug_text = None
    debug_label = None
    pending_delete = False

    def __init__(self, img, x, y):
        self.radius = int(img.width / 2)
        img.anchor_x = img.width // 2
        img.anchor_y = img.height // 2
        super().__init__(img, x, y)

    def update_debug_label(self):
        if not self.debug_text:
            return
        if self.debug_label:
            self.debug_label.text = self.debug_text
        else:
            x = self.x - self.image.anchor_x
            y = self.y - self.image.anchor_y
            self.debug_label = pyglet.text.Label(text=self.debug_text, 
                    x=x, y=y, multiline=True, width=500)
            self.link(self.debug_label)
    
    def die(self, *args):
        self.delete()
        self.pending_delete = True

class CollidableSprite(BaseSprite):
    """
    Provides methods for computing the (x, y) coordinates
    a sprite occupies.
    """

    def collision_cells(self):
        current_x = int(self.x)
        current_y = int(self.y)
        for y in range(current_y - self.radius, current_y + self.radius + 1):
            for x in range(current_x - self.radius, current_x + self.radius + 1):
                yield (x, y)

class MovingSprite(BaseSprite):
    dx = 0
    dy = 0
    
    def update(self, dt):
        self.x = int(self.x + self.dx * dt)
        self.y = int(self.y + self.dy * dt)
        if hasattr(self, 'rotation_speed'):
            self.rotation += (self.rotation_speed * dt)
        super().update(dt)
        self.check_bounds()

    @property
    def debug_text(self):
        s = self.__class__.__name__ + '\n'
        s += f'({self.x}, {self.y})\n'
        dx = int(self.dx)
        dy = int(self.dy)
        rot = int(self.rotation)
        s += f'dx={dx} dy={dy} r={rot}\n'
        return s

class Asteroid(MovingSprite, CollidableSprite, BaseSprite):
    max_rotation_speed = 10.0

    def __init__(self, img, x, y):
        super().__init__(img, x, y)

        #self.dx = -random.randint(10, 40)
        self.dx = -100
        self.rotation = random.random() * 360.0
        self.rotation_speed = random.random() * self.max_rotation_speed

    def check_bounds(self):
        """
        Asteroids should be deleted when they leave the viewport on the left side.
        """
        if self.x <= -self.image.width:
            raise SpriteOutOfBounds()

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

class Bullet(MovingSprite, CollidableSprite, BaseSprite):
    debug_text = None
    bullet_speed = 700.0

    def __init__(self, *args, **kwargs):
        img = resource.image('bullet.png')
        super().__init__(img, *args, **kwargs)
        self.dx = 500

    def check_bounds(self):
        """
        Bullets are deleted when they leave the viewport on right side.
        """
        if self.x >= WINDOW_WIDTH:
            raise SpriteOutOfBounds(self)

class Ship(MovingSprite, CollidableSprite, BaseSprite):
    max_speed = 200.0
    fire_timeout = 0

    def __init__(self, img, key_handler):
        initial_x = WINDOW_WIDTH // 6
        initial_y = WINDOW_HEIGHT // 2

        super().__init__(img, initial_x, initial_y)

        self.rotation = 90
        self.key_handler = key_handler

    def update(self, dt):
        if self.key_handler[key.UP]:
            self.dy += self.max_speed * dt

        if self.key_handler[key.DOWN]:
            self.dy -= self.max_speed * dt

        if self.key_handler[key.LEFT]:
            self.dx -= self.max_speed * dt

        if self.key_handler[key.RIGHT]:
            self.dx += self.max_speed * dt

        if self.debug_label:
            self.update_debug_label()

        self.fire_timeout -= dt

        super().update(dt)

    def check_bounds(self):
        """
        Ships should be blocked from going out of the viewport
        by stopping their velocity.
        """
        if self.x > WINDOW_WIDTH or self.x < 0:
            self.dx = 0
        if self.y > WINDOW_HEIGHT or self.y < 0:
            self.dy = 0

    def fire(self):
        bullet = None
        if self.fire_timeout <= 0:
            self.fire_timeout = 0.1
            bullet = Bullet(x=self.x, y=self.y)
        return bullet

class Game(pyglet.window.Window):
    sprites = []
    hits = None
    start_time = 0

    def __init__(self, *args, **kwargs):
        self.debug = kwargs.pop('debug', False)

        # super() must be called before setting dimmensions
        super().__init__(*args, **kwargs)

        global WINDOW_WIDTH, WINDOW_HEIGHT
        WINDOW_WIDTH = self.width
        WINDOW_HEIGHT = self.height

        self.key_handler = key.KeyStateHandler()
        self.push_handlers(self.key_handler)

        # 1. set up static sprites: must be first (bottom layer)
        self.sprites.append(pyglet.sprite.Sprite(resource.image('white.png'), 0, 0))
        self.sprites.append(StarImageField(resource.image('star.jpg')))
        self.asteroid_grid = pyglet.image.ImageGrid(resource.image('asteroids.png'), 8, 8)

        # 2. HUD
        hud_padding = 40
        self.fps = pyglet.window.FPSDisplay(self)
        self.fps.label.y = WINDOW_HEIGHT - 40
        self.elapsed_label = pyglet.text.Label(text='0', anchor_x='right',
                x=WINDOW_WIDTH - 10, y=hud_padding)

        # 3. player ship
        self.ship = Ship(resource.image('ship.png'), self.key_handler)
        self.push_handlers(self.ship.key_handler)
        self.sprites.append(self.ship)

        self.start_time = time.time()
        pyglet.clock.schedule_once(self.new_asteroids, 1)
        pyglet.clock.schedule_interval(self.update, 1/120.0)

    @property
    def elapsed_time(self):
        return time.time() - self.start_time

    def on_draw(self):
        self.clear()

        for sprite in self.sprites:
            sprite.draw()
            if self.debug and hasattr(sprite, 'update_debug_label'):
                sprite.update_debug_label()

        self.elapsed_label.draw()
        self.fps.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            sys.exit()
        return pyglet.event.EVENT_HANDLED

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            sprite = self.hits.get(x+y, None)
            print('clicked', sprite)

    def update(self, dt):
        self.elapsed_label.text = str(round(self.elapsed_time, 2))

        if self.key_handler[key.SPACE]:
            bullet = self.ship.fire()
            if bullet:
                self.sprites.append(bullet)

        try:
            for sprite in self.sprites:
                if hasattr(sprite, 'update'):
                    sprite.update(dt)
                if getattr(sprite, 'pending_delete', False):
                    self.sprites.remove(sprite)

            self.update_collision_cells()
        except (DeleteSprite, SpriteOutOfBounds) as e:
            e.obj.delete()
            self.sprites.remove(e.obj)
            print('Deleted', e.obj, 'at', e.obj.x, e.obj.y)

    def get_empty_coords(self, width, height):
        """
        Naive method for returning random right-side coords that
        are not occupied by any other sprite.
        """
        while True:
            x = WINDOW_WIDTH + (width * 2)
            y = random.randint(height, WINDOW_HEIGHT - height)
            hit = self.hits.get(x+y, None)
            if not hit:
                return (x, y)

    def get_asteroids(self, num):
        """
        Generate a number of asteroids sprites at random right-side coords
        and return them as  list.
        """
        asteroids = []
        for i in range(num):
            img = self.asteroid_grid[(random.randint(0, 7), random.randint(0, 7))]
            x, y = self.get_empty_coords(img.width, img.height)
            asteroids.append(Asteroid(img=img, x=x, y=y))
        return asteroids

    def check_collisions(self):
        for pos, sprites in self.hits.items():
            if len(sprites) > 1:
                raise CollisionBetween(sprites, pos)

    def update_collision_cells(self):
        hits = {}
        for sprite in [s for s in self.sprites if hasattr(s, 'collision_cells')]:
            for x, y in sprite.collision_cells():
                i = x + y
                occupies = hits.setdefault(i, set())
                occupies.add(sprite)
                if len(occupies) > 1:
                    # prevent bullets from colliding with ourself
                    if len(set([type(x) for x in occupies]) - {Ship, Bullet}) > 0:
                        for sprite in occupies:
                            sprite.die()
        self.hits = hits

    def new_asteroids(self, dt):
        if self.elapsed_time < 2:
            num = 1
        else:
            num = random.randint(0, 2)
        self.sprites.extend(self.get_asteroids(num))
        pyglet.clock.schedule_once(self.new_asteroids, random.randint(4, 6))


def main():
    window = Game(
        fullscreen=True,
        caption='Asteroids',
        debug=True,
    )
    pyglet.app.run()
