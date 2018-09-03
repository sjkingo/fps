import pyglet
from pyglet.gl import *
from pyglet import resource

import random

window = pyglet.window.Window(
    fullscreen=True,
    caption='Game',
)

resource.path = ['fps/resources']
resource.reindex()

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
        self.x = wrap(x, window.width)
        self.y = wrap(y, window.height)
        self.rotation = wrap(rotation, 360.0)

asteroids_img = resource.image('asteroids.png')
asteroids_grid = pyglet.image.ImageGrid(asteroids_img, 8, 8)

class Asteroid(MovingSprite):
    MAX_ROTATION_SPEED = 20.0

    def __init__(self, img, x, y, batch=None):
        super().__init__(img, x, y, batch=batch)
        self.dx = (random.random() - 0.5) * 25
        self.dy = (random.random() - 0.5) * 25
        self.rotation = random.random() * 360.0
        #self.rotation_speed = (random.random() - 0.5) * self.MAX_ROTATION_SPEED
        self.rotation_speed = random.random() * self.MAX_ROTATION_SPEED

def get_asteroids(num=10, batch=None):
    asteroids = []
    for i in range(num):
        x = random.randint(0, window.width)
        y = random.randint(0, window.height)
        index = (random.randint(0, 7), random.randint(0, 7))
        asteroid = Asteroid(img=asteroids_grid[index], x=x, y=y, batch=batch)
        asteroid.rotation = random.randint(0, 360)
        asteroids.append(asteroid)
    return asteroids

asteroid_batch = pyglet.graphics.Batch()
asteroids = get_asteroids()#batch=asteroid_batch)
#asteroid_batch.draw()

class Stars:
    """
    Background star field that "floats" across window.
    TODO: dynamically add new sprites when the image scrolls off screen.
    """

    def __init__(self, img, x, y):
        self.img = img
        self.x = x
        self.y = y
        # move SE
        self.dx = 4
        self.dy = -self.dx

    def update(self, dt):
        self.x += self.dx * dt
        self.y += self.dy * dt

    def draw(self):
        self.img.blit(self.x, self.y)

stars = Stars(resource.image('star.jpg'), 0, 0)

@window.event
def on_draw():
    window.clear()
    stars.draw()
    for asteroid in asteroids:
        asteroid.draw()
    #asteroid_batch.draw()

def update(dt):
    stars.update(dt)
    for asteroid in asteroids:
        asteroid.update(dt)

pyglet.clock.schedule_interval(update, 1/120.0)

def main():
    pyglet.app.run()
