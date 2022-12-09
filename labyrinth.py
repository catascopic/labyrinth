import abc
import random
import itertools
import json

from collections import deque, defaultdict
from typing import Union, Callable
from dataclasses import dataclass
from enum import Enum, Flag, auto


class Serializable(abc.ABC):
	def to_json(self):
		return NotImplemented


class CustomJson(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, Serializable):
			return obj.to_json()
		if isinstance(obj, deque):
			return list(obj)
		return json.JSONEncoder.default(self, obj)


JSON = CustomJson()


class Direction(Flag):
	NORTH = 1
	EAST = 2
	SOUTH = 4
	WEST = 8
	NE = NORTH | EAST
	NW = NORTH | WEST
	SE = SOUTH | EAST
	SW = SOUTH | WEST
	NS = NORTH | SOUTH
	EW = EAST | WEST
	NSE = NORTH | SOUTH | EAST
	NSW = NORTH | SOUTH | WEST
	NEW = NORTH | EAST | WEST
	SEW = SOUTH | EAST | WEST
	# For testing only:
	NSEW = NORTH | SOUTH | EAST | WEST

	def __lshift__(self, amount):
		amount %= 4
		rotated = self.value << amount
		return Direction(rotated & 0xF | (rotated & 0xF0) >> 4)

	def __rshift__(self, amount):
		return self.__lshift__(-amount)


class Quest(Enum):
	BAT = 'A'
	BOOK = 'B'
	CANDELABRA = 'C'
	DRAGON = 'D'
	EMERALD = 'E'
	GHOST = 'G'
	HELMET = 'H'
	SPIDER = 'I'
	GENIE = 'J'
	KEYS = 'K'
	LIZARD = 'L'
	MAP = 'M'
	CROWN = 'N'
	OWL = 'O'
	POUCH = 'P'
	GOBLIN = 'Q'
	RING = 'R'
	SCARAB = 'S'
	CHEST = 'T'
	SKULL = 'U'
	WITCH = 'W'
	SWORD = 'X'
	MOUSE = 'Y'
	MOTH = 'Z'

	def __str__(self):
		return f"{self.name} ({self.value})"


class Color(Enum):
	RED = auto()
	YELLOW = auto()
	BLUE = auto()
	GREEN = auto()

	def __repr__(self):
		return f"{self.name} start ({self.value})"


@dataclass
class Tile(Serializable):
	path: Direction
	item: Union[Quest, Color, None]

	@property
	def symbol(self):
		return self.item.value if self.item else ' '

	def __repr__(self):
		return f"{self.path.name} {self.item}"

	def box_drawing_lines(self, symbol=None):
		north = '╨' if self.path & Direction.NORTH else '─'
		west = '═╡' if self.path & Direction.WEST else ' │'
		east = '╞═' if self.path & Direction.EAST else '│ '
		south = '╥' if self.path & Direction.SOUTH else '─'
		if symbol is None:
			symbol = self.symbol
		return [
			f" ╭─{north}─╮ ",
			f"{west}{symbol:^3}{east}",
			f" ╰─{south}─╯ ",
		]

	def to_json(self):
		return {
			'paths': [d.name for d in self.path],
			'item': None if not self.item else self.item.name,
		}


def rotate_column(grid, index, sign):
	# maybe not most efficient space-wise... but really short!
	col = deque(row[index] for row in grid)
	col.rotate(sign)
	for row, v in zip(grid, col):
		row[index] = v


def chunks(items, n):
	for i in range(0, len(items), n):
		yield items[i:i + n]


PLAYER_START = {
	Color.RED: (0, 0),
	Color.YELLOW: (0, 7),
	Color.GREEN: (7, 0),
	Color.BLUE: (7, 7),
}


@dataclass
class Player(Serializable):
	client: Callable
	color: Color
	items: deque[Quest]
	i: int
	j: int

	def move(self, game):
		self.client(self, game)
		# self.client(JSON.encode({
		# 	'color': self.color.name,
		# 	'quest': self.items[0].name,
		# 	'players': {p.color.name: p for p in game.players},
		# 	'board': game.board,
		# }))

	def to_json(self):
		return {
			'pos': [self.i, self.j],
			'remaining': len(self.items),
		}


class Game:

	def __init__(self, players: list[tuple[Color, Callable]]):
		self.board = [
			[
				Tile(Direction.SE, Color.RED),
				None,
				Tile(Direction.SEW, Quest.BOOK),
				None,
				Tile(Direction.SEW, Quest.POUCH),
				None,
				Tile(Direction.SW, Color.YELLOW),
			],
			deque([None] * 7),
			[
				Tile(Direction.NSE, Quest.MAP),
				None,
				Tile(Direction.NSE, Quest.CROWN),
				None,
				Tile(Direction.SEW, Quest.KEYS),
				None,
				Tile(Direction.NSW, Quest.SKULL),
			],
			deque([None] * 7),
			[
				Tile(Direction.NSE, Quest.RING),
				None,
				Tile(Direction.NEW, Quest.CHEST),
				None,
				Tile(Direction.NSW, Quest.EMERALD),
				None,
				Tile(Direction.NSW, Quest.SWORD),
			],
			deque([None] * 7),
			[
				Tile(Direction.NE, Color.GREEN),
				None,
				Tile(Direction.NEW, Quest.CANDELABRA),
				None,
				Tile(Direction.NEW, Quest.HELMET),
				None,
				Tile(Direction.NW, Color.BLUE),
			],
		]

		loose_tiles = [
			Tile(Direction.NEW, Quest.BAT),
			Tile(Direction.NEW, Quest.DRAGON),
			Tile(Direction.NEW, Quest.GENIE),
			Tile(Direction.NEW, Quest.GHOST),
			Tile(Direction.NEW, Quest.GOBLIN),
			Tile(Direction.NEW, Quest.WITCH),
			Tile(Direction.NE, Quest.LIZARD),
			Tile(Direction.NE, Quest.MOTH),
			Tile(Direction.NE, Quest.MOUSE),
			Tile(Direction.NE, Quest.SPIDER),
			Tile(Direction.NE, Quest.OWL),
			Tile(Direction.NE, Quest.SCARAB),
			*(Tile(Direction.EW, None) for _ in range(13)),
			*(Tile(Direction.NE, None) for _ in range(9)),
		]

		random.shuffle(loose_tiles)
		for tile in loose_tiles:
			tile.path <<= random.randint(0, 3)

		for i in range(7):
			for j in range(7):
				if i % 2 or j % 2:  # non-fixed tiles occur when either coordinate is odd
					self.board[i][j] = loose_tiles.pop()

		self.free = loose_tiles.pop()

		self.graph = compute_graph(self.board)

		deck = list(Quest)
		random.shuffle(deck)
		self.players = []
		for (color, client), items in zip(players, chunks(deck, 24 // len(players))):
			items.append(color)
			self.players.append(Player(client, color, items, *PLAYER_START[color]))

		self.winners = []
		self.move_history = []

	def shift(self, direction: Direction, index: int, rotation: int):
		if not index % 2:
			raise ValueError(f"board is fixed at row/col {index}")

		self.free.path <<= rotation

		if direction & Direction.NW:
			eject_index = 0
			sign = 1
		else:
			eject_index = 6
			sign = -1

		if direction & Direction.EW:
			row = self.board[index]
			row.rotate(sign)
			self.free, row[eject_index] = row[eject_index], self.free
		else:
			rotate_column(self.board, index, sign)
			self.free, self.board[eject_index][index] = self.board[eject_index][index], self.free
		self.graph = compute_graph(self.board)

	def print_board(self, symbol=None):
		if symbol is None:
			def symbol(_i, _j, tile):
				return tile.symbol
		for i, row in enumerate(self.board):
			for lines in zip(*(t.box_drawing_lines(symbol(i, j, t)) for j, t in enumerate(row))):
				print(''.join(lines))

	def print_sectors(self):
		def sector(adj):
			si, sj = min(adj)
			return f"{si},{sj}"

		sectors = {node: sector(adj) for node, adj in self.graph.items()}
		self.print_board(lambda i, j, _: sectors[(i, j)])

	def print_free(self):
		for line in self.free.box_drawing_lines():
			print(line)

	def pretend_move(self, ):
		pass

	def play(self):
		for player in itertools.cycle(self.players):
			if player.items:
				direction, index, rotation, i, j = player.client(self)
				last_dir, last_index, *_ = game.move_history[-1]
				if direction == last_dir << 2 and index == last_index:
					raise ValueError("Can't reverse last move")
				game.shift(direction, index, rotation)
				if (i, j) not in game.graph[(player.i, player.j)]:
					raise ValueError(f"{player.color} can't move to {i},{j}")
				player.i = i
				player.j = j
				game.move_history.append((direction, index, rotation, i, j))
				if game.board[i][j].item == player.items[0]:
					player.items.popleft()
					if not player.items:
						game.winners.append(player.color)
						if len(game.winners) == len(game.players) - 1:
							return


NAVIGATION = [
	(Direction.NORTH, -1, 0),
	(Direction.EAST, 0, 1),
	(Direction.SOUTH, 1, 0),
	(Direction.WEST, 0, -1),
]


def get_adjacent(board, i, j):
	tile = board[i][j]
	for dir_, di, dj in NAVIGATION:
		ai = i + di
		aj = j + dj
		if tile.path & dir_ and 0 <= ai < 7 and 0 <= aj < 7:
			if board[ai][aj].path & (dir_ << 2):
				yield ai, aj


def traverse(board, i, j, explored):
	explored.add((i, j))
	for adj in get_adjacent(board, i, j):
		if adj not in explored:
			ci, cj = adj
			traverse(board, ci, cj, explored)


def compute_graph(board):
	graph = {}
	for i in range(7):
		for j in range(7):
			if (i, j) not in graph:
				explored = set()
				traverse(board, i, j, explored)
				for node in explored:
					graph[node] = explored
	return graph


def random_player(game, player):
	moves = set(itertools.product([1, 3, 5], Direction))
	if game.move_history:
		moves.remove(game.move_history[-1][:2])
	return random.choice(list(moves)), random.choice(list(game.graph[(player.i, player.j)]))


game = Game([(Color.RED, print), (Color.BLUE, print)])
game.print_board()
print('REMAINING:')
game.print_free()
game.print_sectors()
# game.shift(Direction.SOUTH, 1, 0)
# print('AFTER SHIFT')
# game.print_board()
# game.print_free()
# game.print_sectors()
print(random_player(game, game.players[0]))
