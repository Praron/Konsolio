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
ROBOHAND_PAIR = 4
PISTON_PAIR = 5

UP = 0
RIGHT = 90
DOWN = 180
LEFT = 270


class Context(Enum):
    WORLD = 1
    X = 2
    Y = 3
    SCR = 4


def get_ch(scr, x, y):
    return chr(scr.inch(y, x) & 0xFF)


class Entity():
    def __init__(self):
        self.context = None
        self.moveable = False
        self.is_moved = False
        self.solid = False
        self.ch = '?'
        self.color_pair = curses.color_pair(ERROR_PAIR)

    def act(self):
        pass

    def draw(self, scr):
        if get_ch(scr, self.x, self.y) == ' ':
            scr.addch(self.y, self.x, self.ch, self.color_pair)

    @property
    def x(self):
        return self.context[Context.X]

    @property
    def y(self):
        return self.context[Context.Y]

    @property
    def world(self):
        return self.context[Context.WORLD]

    @property
    def scr(self):
        return self.context[Context.SCR]


class Floor(Entity):
    def __init__(self):
        super().__init__()
        self.ch = '.'
        self.color_pair = curses.color_pair(BACKGROUND_PAIR)


class Item(Entity):
    def __init__(self):
        super().__init__()
        self.moveable = True


class TestItem(Item):
    def __init__(self):
        super().__init__()
        self.ch = '$'


class Transport(Item):
    def __init__(self, angle=UP):
        super().__init__()
        self.angle = angle
        self.rotate(angle)
        self.color_pair = curses.color_pair(TRANSPORT_PAIR)

    def _upd_ch(self):
        self.ch = {UP: '^',
                   RIGHT: '>',
                   DOWN: 'v',
                   LEFT: '<'}[self.angle]

    def rotate(self, angle=None):
        self.angle = self.angle + 90 if angle is None else angle
        self._upd_ch()

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


class Piston(Item):

    class MovingPart(Item):
        def __init__(self, parent):
            super().__init__()
            self.moved_on = 0
            self.solid = parent.solid
            self.angle = parent.angle
            self.parent = parent
            self.color_pair = parent.color_pair
            self.ch = {UP: curses.ACS_TTEE,
                       RIGHT: curses.ACS_RTEE,
                       DOWN: curses.ACS_BTEE,
                       LEFT: curses.ACS_LTEE}[self.angle]

        def act(self):
            dx, dy = {UP: (0, -1),
                      DOWN: (0, 1),
                      RIGHT: (1, 0),
                      LEFT: (-1, 0)}[self.angle]
            tile = self.world[self.x + dx][self.y + dy]
            if (self.world.turns - self.moved_on == 1):
                dx = self.parent.x - self.x
                dy = self.parent.y - self.y
                self.world.move(self, dx=dx // 2, dy=dy // 2)

            elif len(tile) >= 2 and self.world.turns - self.moved_on > 1:
                items = tile[1:]
                self.moved_on = self.world.turns
                for i in items:
                    self.world.move(i, dx=dx, dy=dy)
                    self.world.move(self, dx=dx, dy=dy)

    def __init__(self, angle=UP):
        super().__init__()
        self.solid = True
        self.color_pair = curses.color_pair(PISTON_PAIR)
        self.angle = angle
        self.ch = {UP: 'L',
                   RIGHT: '[',
                   DOWN: curses.ACS_PI,
                   LEFT: ']'}[self.angle]
        self.have_part = False
        self.part = Piston.MovingPart(self)

    def init_part(self):
        dx, dy = {UP: (0, -1),
                  DOWN: (0, 1),
                  RIGHT: (1, 0),
                  LEFT: (-1, 0)}[self.angle]
        self.world.add(self.part, self.x + dx, self.y + dy)

    def act(self):
        if not self.have_part:
            self.init_part()
            self.have_part = True
        self.part.act()


class Robohand(Item):

    class Hand(Item):
        def __init__(self, parent, angle=UP):
            super().__init__()
            self.parent = parent
            self.color_pair = curses.color_pair(ROBOHAND_PAIR)
            self.angle = angle
            self.ch = {UP: 'v',
                       RIGHT: '<',
                       DOWN: '^',
                       LEFT: '>'}[self.angle]
            self.solid = True

    def __init__(self, angle=UP):
        super().__init__()
        self.color_pair = curses.color_pair(ROBOHAND_PAIR)
        self.angle = angle
        self.ch = '%'
        self.solid = True
        self.hand = Robohand.Hand(self, angle=angle)
        self.have_hand = False

    def get_offset(self):
        return {UP: (0, -2),
                RIGHT: (2, 0),
                DOWN: (0, 2),
                LEFT: (-2, 0)}[self.angle]

    def init_hand(self):
            dx, dy = {UP: (0, -1),
                      DOWN: (0, 1),
                      RIGHT: (1, 0),
                      LEFT: (-1, 0)}[self.angle]
            self.world.add(self.hand, self.x + dx, self.y + dy)

    def act(self):
        if not self.have_hand:
            self.init_hand()
            self.have_hand = True


class Player(Entity):
    def __init__(self):
        super().__init__()
        self.ch = '@'
        self.color_pair = curses.color_pair(PLAYER_PAIR)

    def get_item(self):
        if type(self.world.get_under(self)) != Floor:
            self.world.delete_entity(self.world.get_under(self))


def fill(scr, color):
    h, w = scr.getmaxyx()
    for y in range(h - 1):
        scr.insstr(y, 0, '.' * (w - 1), color)


class World():
    def __init__(self, scr, w, h):
        self.scr, self.w, self.h = scr, w, h
        self.turns = 0
        self._w = [[[Floor()] for y in range(h)] for x in range(w)]
        for y in range(h):  # Bad code!
            for x in range(w):
                self.add_context_to(x, y, self[x][y][0])

    def __getitem__(self, key):
        return self._w[key]

    def add_context_to(self, x, y, entity):
        context = {Context.WORLD: self, Context.X: x, Context.Y: y,
                   Context.SCR: self.scr}
        entity.context = context

    # Use or coordinates, or upper object
    def add(self, entity, x=None, y=None, under=None):
        if under:
            tile = self[under.x][under.y]
            tile.insert(tile.index(under), entity)
            self.add_context_to(under.x, under.y, entity)
        elif type(x) == type(y) == int:
            tile = self[x][y]
            tile.append(entity)
            self.add_context_to(x, y, entity)
        else:
            raise ValueError("World.add(): must define 'x' and 'y' or 'under'")
        return self

    def draw(self, scr):
        scr.clear()
        for y in range(self.h):
            for x in range(self.h):
                self[x][y][-1].draw(scr)
        scr.refresh()

    def delete_entity(self, ent):
        tile = self[ent.x][ent.y]
        tile.pop(tile.index(ent))

    def _move_abs(self, entity, x, y):
        self.delete_entity(entity)
        self[x][y].append(entity)
        self.add_context_to(x, y, entity)

    def _move_rel(self, entity, dx, dy):
        self._move_abs(entity, x=entity.x + dx, y=entity.y + dy)

    def move(self, entity, x=None, y=None, dx=0, dy=0):
        if type(x) == type(y) == int:
            self._move_abs(entity, x, y)
        else:
            self._move_rel(entity, dx, dy)

    def tile_free(self, x, y):
        return all([not e.solid for e in self[x][y]])

    def move_player(self, player, key):
        dx = -1 if key == 'h' else 1 if key == 'l' else 0
        dy = -1 if key == 'k' else 1 if key == 'j' else 0
        if self.tile_free(player.x + dx, player.y + dy):
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
        return self.get_above_all(entity)[0]

    def get_tiles(self):
        return [tile for sublist in self._w for tile in sublist]

    def get_entities(self):
        return [ent for tile in self.get_tiles() for ent in tile]

    def free_all_moveable(self):
        for entity in self.get_entities():
            entity.is_moved = False

    def act(self):
        self.turns += 1
        for entity in self.get_entities():
            entity.act()
        self.free_all_moveable()


def init_pairs():
    curses.init_pair(PLAYER_PAIR, YELLOW, BLUE)
    curses.init_pair(ERROR_PAIR, YELLOW, RED)
    curses.init_pair(TRANSPORT_PAIR, BLUE, CYAN)
    curses.init_pair(ROBOHAND_PAIR, RED, GREEN)
    curses.init_pair(PISTON_PAIR, YELLOW, GREEN)


def init_scr(scr):
    scr.clear()
    curses.curs_set(False)
    init_pairs()
    curses.halfdelay(5)


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
        world.add(TestItem(), under=player)
    elif key == 'd':
        player.get_item()
    elif key == 'w':
        key_2 = get_key(scr)
        if key_2 in 'hjkl':
            angle = {'h': LEFT,
                     'j': DOWN,
                     'k': UP,
                     'l': RIGHT}[key_2]
            world.add(Transport(angle=angle), under=player)
            world.move_player(player, key_2)
    elif key == 'e':
        key_2 = get_key(scr)
        if key_2 in 'hjkl':
            angle = {'h': LEFT,
                     'j': DOWN,
                     'k': UP,
                     'l': RIGHT}[key_2]
            world.add(Robohand(angle=angle), under=player)
            if key_2 == 'h': world.move_player(player, 'l')
            if key_2 == 'j': world.move_player(player, 'k')
            if key_2 == 'k': world.move_player(player, 'j')
            if key_2 == 'l': world.move_player(player, 'h')
    elif key == 'r':
        key_2 = get_key(scr)
        if key_2 in 'hjkl':
            angle = {'h': LEFT,
                     'j': DOWN,
                     'k': UP,
                     'l': RIGHT}[key_2]
            world.add(Piston(angle=angle), under=player)
            if key_2 == 'h': world.move_player(player, 'l')
            if key_2 == 'j': world.move_player(player, 'k')
            if key_2 == 'k': world.move_player(player, 'j')
            if key_2 == 'l': world.move_player(player, 'h')


def main(stdscr):
    init_scr(stdscr)

    world = World(stdscr, 15, 10)
    player = Player()
    world.add(player, 5, 5)
    while True:
        world.draw(stdscr)
        world.act()
        handle_input(stdscr, world, player)


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
