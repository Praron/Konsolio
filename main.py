import curses
from enum import Enum

WHITE = curses.COLOR_WHITE
BLACK = curses.COLOR_BLACK
RED = curses.COLOR_RED
BLUE = curses.COLOR_BLUE
CYAN = curses.COLOR_CYAN
GREEN = curses.COLOR_GREEN
YELLOW = curses.COLOR_YELLOW
MAGNETA = curses.COLOR_MAGENTA

BACKGROUND_PAIR = 0
PLAYER_PAIR = 1
ERROR_PAIR = 2
TRANSPORT_PAIR = 3

UP = 0
RIGHT = 90
DOWN = 180
LEFT = 270


class Context(Enum):
    WORLD = 1
    X = 2
    Y = 3


class Entity():
    def __init__(self, x, y):
        # self._x, self._y = x, y
        self.context = None
        self.moveable = False
        self.is_moved = False
        self.ch = '?'
        self.color_pair = curses.color_pair(ERROR_PAIR)

    def act(self):
        pass

    @property
    def x(self):
        # return self._x
        self.context[Context.X]

    @property
    def y(self):
        # return self._y
        self.context[Context.Y]

    @x.setter
    def x(self, x):
        self._x = x

    @y.setter
    def y(self, y):
        self._y = y


class Floor(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.ch = '#'
        self.color_pair = curses.color_pair(BACKGROUND_PAIR)


class Item(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.moveable = True


class TestItem(Item):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.ch = '$'


class Transport(Item):
    def __init__(self, x, y, angle=RIGHT):
        super().__init__(x, y)
        self.angle = angle
        self.rotate(angle)
        self.color_pair = curses.color_pair(TRANSPORT_PAIR)

    def rotate(self, angle=None):
        if angle is None:
            self.angle += 90
        else:
            self.anlge = angle
        self.ch = {UP: '^',
                   RIGHT: '>',
                   DOWN: 'v',
                   LEFT: '<'}[self.angle]

    def get_offset(self):
        return {UP: (0, -1),
                RIGHT: (1, 0),
                DOWN: (0, 1),
                LEFT: (-1, 0)}[self.angle]

    def act(self):
        dx, dy = self.get_offset()
        for entity in self.world.get_above_all(self):
            if entity.moveable and not entity.is_moved:
                self.world.move(entity, dx=dx, dy=dy)
                entity.is_moved = True


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.ch = '@'
        self.color_pair = curses.color_pair(PLAYER_PAIR)

    def get_upper(self):
        if type(self.world.get_under(self)) != Floor:
            self.world.delete_entity(self.world.get_under(self),
                                     self.x, self.y)


def fill(scr, color):
    h, w = scr.getmaxyx()
    for y in range(h - 1):
        scr.insstr(y, 0, '.' * (w - 1), color)


class World():
    def __init__(self, w, h):
        self.w, self.h = w, h
        self._w = [[[Floor(x, y)] for x in range(w)] for y in range(h)]

    def __getitem__(self, key):
        return self._w[key]

    def add_context_to(self, x, y, entity):
        context = {Context.WORLD: self, Context.X: x, Context.Y: y}
        entity.context = context

    def add(self, entity, x, y, under=None):
        # entity.world = self
        self.add_context_to(entity, x, y)
        if under:
            tile = self[under.x][under.y]
            tile.insert(tile.index(under), entity)
        # elif entity is not None:
        else:
            tile = self[x][y]
            tile.append(entity)
        # else:
        #     raise ValueError("Must be defined 'entity' or 'under' argument")
        return self

    def draw(self, scr):
        scr.clear()
        for y in range(self.h):
            for x in range(self.h):
                ent = self[x][y][-1]
                scr.insch(y, x, ent.ch, ent.color_pair)

        scr.refresh()

    def delete_entity(self, ent, x, y):
        tile = self[ent.x][ent.y]
        tile.pop(tile.index(ent))

    def _move_abs(self, entity, x, y):
        self.delete_entity(entity, x, y)
        self[x][y].append(entity)
        entity.x, entity.y = x, y

    def _move_rel(self, entity, dx, dy):
        self._move_abs(entity, x=entity.x + dx, y=entity.y + dy)

    def move(self, entity, x=None, y=None, dx=0, dy=0):
        if type(x) == type(y) == int:
            self._move_abs(entity, x, y)
        else:
            self._move_rel(entity, dx, dy)

    def move_player(self, player, key):
        dx = -1 if key == 'h' else 1 if key == 'l' else 0
        dy = -1 if key == 'k' else 1 if key == 'j' else 0
        self.move(player, dx=dx, dy=dy)

    def get_under_all(self, entity):
        tile = self[entity.x][entity.y]
        return tile[:tile.index(entity)]

    def get_under(self, entity):
        return self.get_under_all(entity)[-1]

    def get_above_all(self, entity):
        tile = self[entity.x][entity.y]
        return tile[1 + tile.index(entity):]

    def get_above(self, entity):
        return self.get_above_all(entity)[-1]

    def get_tiles(self):
        return [tile for sublist in self._w for tile in sublist]

    def get_entities(self):
        return [ent for tile in self.get_tiles() for ent in tile]

    def free_moveable(self):
        for entity in self.get_entities():
            entity.is_moved = False

    def act(self):
        for entity in self.get_entities():
            entity.act()
        self.free_moveable()


def init_pairs():
    curses.init_pair(PLAYER_PAIR, YELLOW, BLUE)
    curses.init_pair(ERROR_PAIR, YELLOW, RED)
    curses.init_pair(TRANSPORT_PAIR, BLUE, CYAN)


def init_scr(scr):
    scr.clear()
    curses.curs_set(False)
    init_pairs()


def get_key(scr):
    try:
        return scr.getkey()
    except curses.error:
        return 'no_input'


def handle_input(scr, world, player):
    key = get_key(scr)
    if key in 'hjkl':
        world.move_player(player, key)
    elif key == 'q':
        world.add(TestItem(player.x, player.y), under=player)
    elif key == 'd':
        player.get_upper()
    elif key == 'w':
        key_2 = get_key(scr)
        if key_2 in 'hjkl':
            angle = {'h': LEFT,
                     'j': DOWN,
                     'k': UP,
                     'l': RIGHT}[key_2]
            world.add(Transport(player.x, player.y, angle=angle), under=player)
            world.move_player(player, key_2)


def main(stdscr):

    init_scr(stdscr)
    curses.halfdelay(5)

    world = World(15, 10)
    player = Player(5, 5)
    world.add(player, 5, 5)
    while True:
        world.act()
        world.draw(stdscr)
        handle_input(stdscr, world, player)


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
