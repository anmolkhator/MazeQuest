"""The maze as a graph: each cell is a vertex, each missing wall is an edge.
Walls are stored as a bitmask per cell (N=1, E=2, S=4, W=8)."""
N, E, S, W = 1, 2, 4, 8
DIRS = [(-1, 0, N, S), (0, 1, E, W), (1, 0, S, N), (0, -1, W, E)]   # (dr, dc, wall bit, opposite bit)


class Maze:
    def __init__(self, n):
        self.n = n
        self.walls = [15] * (n * n)
        self.cost = [1] * (n * n)
        self.start, self.goal = 0, n * n - 1

    def inb(self, i, d):
        r, c = divmod(i, self.n)
        return 0 <= r + DIRS[d][0] < self.n and 0 <= c + DIRS[d][1] < self.n

    def step(self, i, d):
        return i + DIRS[d][0] * self.n + DIRS[d][1]

    def carve(self, i, d):                      # remove the wall between i and its neighbour
        j = self.step(i, d)
        self.walls[i] &= ~DIRS[d][2]
        self.walls[j] &= ~DIRS[d][3]

    def open(self, i, d):                       # can we walk from i in direction d?
        return self.inb(i, d) and not self.walls[i] & DIRS[d][2]

    def neighbors(self, i):
        return [self.step(i, d) for d in range(4) if self.open(i, d)]
