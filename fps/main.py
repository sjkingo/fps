from pyglet import resource
import pyglet
import random

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

class MovingSprite(pyglet.sprite.Sprite):
    dx = 0
    dy = 0
    rotation_speed = 0

    def __init__(self, img, x, y, batch=None):
        super().__init__(img, x, y, batch=batch)
    
    def update(self, dt):
        x = self.x + self.dx * dt
        y = self.y + self.dy * dt
        rotation = self.rotation + self.rotation_speed * dt
        self.x = wrap(x, WINDOW_WIDTH)
        self.y = wrap(y, WINDOW_HEIGHT)
        self.rotation = wrap(rotation, 360.0)

class Asteroid(MovingSprite):
    MAX_ROTATION_SPEED = 20.0

    def __init__(self, img, x, y):
        super().__init__(img, x, y)
        self.dx = (random.random() - 0.5) * 25
        self.dy = (random.random() - 0.5) * 25
        self.rotation = random.random() * 360.0
        self.rotation_speed = random.random() * self.MAX_ROTATION_SPEED

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

class Game(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        num_asteroids = kwargs.pop('asteroids', 10)

        # super() must be called before setting dimmensions
        super().__init__(*args, **kwargs)
        WINDOW_WIDTH = self.width
        WINDOW_HEIGHT = self.height

        # set up sprites
        self.bg = pyglet.sprite.Sprite(resource.image('white.png'), 0, 0)
        self.stars = StarImageField(resource.image('star.jpg'))
        self.asteroids = self.get_asteroids(num_asteroids)

        pyglet.clock.schedule_interval(self.update, 1/120.0)

    def on_draw(self):
        self.clear()
        self.bg.draw()
        self.stars.draw()
        for asteroid in self.asteroids:
            asteroid.draw()

    def update(self, dt):
        self.stars.update(dt)
        for asteroid in self.asteroids:
            asteroid.update(dt)

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

def main():
    window = Game(
        fullscreen=True,
        caption='Asteroids',
    )
    pyglet.app.run()
