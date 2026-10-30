"""Game rules: player position, moves, path cost, win check and score."""
import time
from .solvers import solve


class Game:
    def __init__(self, maze):
        self.maze, self.pos = maze, maze.start
        self.moves = self.spent = 0
        self.t0 = self.t1 = None
        self.over = False

    @property
    def seconds(self):
        return 0.0 if self.t0 is None else (self.t1 or time.time()) - self.t0

    def move(self, d):
        if self.over or not self.maze.open(self.pos, d):
            return False
        self.t0 = self.t0 or time.time()
        self.pos = self.maze.step(self.pos, d)
        self.moves += 1
        self.spent += self.maze.cost[self.pos]
        if self.pos == self.maze.goal:
            self.over, self.t1 = True, time.time()
        return True

    def result(self):
        best = solve(self.maze, "astar", self.maze.start).cost
        eff = round(best / self.spent * 100)
        score = max(0, round(eff * 10 * (self.maze.n / 25) - self.seconds * 2))
        return dict(score=score, eff=eff, best=best, moves=self.moves, cost=self.spent, sec=self.seconds)
