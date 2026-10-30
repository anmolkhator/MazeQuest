"""Settings shared by every module: sizes, algorithm lists, colours."""
SIZES = [15, 25, 35]
BOARD = 640                      # board is drawn inside a 640 px square
WINDOW = (980, 760)
MUD_COST = 5                     # normal tiles cost 1
ALGOS = [("bfs", "Breadth-first"), ("dfs", "Depth-first"), ("dijkstra", "Dijkstra"),
         ("greedy", "Greedy best-first"), ("astar", "A* search")]
GENS = [("dfs", "Backtracker (DFS)"), ("prim", "Prim"), ("kruskal", "Kruskal")]
C = dict(
    g1=(40, 52, 92), g2=(22, 28, 56),                        # calm navy gradient behind everything
    panel=(255, 255, 255), ink=(30, 38, 66), mute=(105, 114, 140), line=(205, 212, 226), white=(255, 255, 255),
    floor=(250, 248, 243), wall=(51, 65, 100), mud=(233, 206, 150), seen=(125, 205, 195), path=(79, 70, 229),
    goal=(34, 160, 90), me=(234, 120, 40), err=(200, 60, 60),
    accent=(79, 70, 229), teal=(13, 148, 136), red=(205, 75, 75))
