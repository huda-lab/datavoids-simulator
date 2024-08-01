from __future__ import annotations
import json
from graph import Graph
from rank import Rank
from agent import Agent
from loaders.load_from_csv import load_csv_files
import networkx as nx

display_params = {
    "fig_size": (10, 10)
}

config = None
database_name = "csvdump"
with open('config.json') as config_file:
  config = json.load(config_file)
  config["database"]["database"] = database_name

print("Initializing graph...")
# load_csv_files("data/example1.nodes.csv", "data/example1.edges.csv", config)
graph = Graph(config)
graph.connect()

graph.cursor.execute("update nodes set active = true")
graph.cursor.execute("update edges set active = true")
graph.conn.commit()

print("Ranking nodes...")
ranking_algorithm = Rank(graph, "searchrank")
ranking_algorithm.rank()

print("Displaying initial graph...")
graph.calculate_node_display_positions(nx.planar_layout)
graph.display_graph(title="Initial graph", **display_params)

print("Initializing disinformer...")
disinformer = Agent(graph, "d", 100, 2)
disinformer.initialize_plan()
graph.display_graph(title="Disinformer initialized plan", **display_params)

mitigator = Agent(graph, "mitigator", 100, 2)
mitigator.initialize_plan()
graph.display_graph(title="Mitigator initialized plan", **display_params)

mitigator_done = False
disinformer_done = False
turn = 0
step_no = 0

while not disinformer_done or not mitigator_done:
  done = True
  if turn == 0 or mitigator_done:
    print("Running disinformer...")
    disinformer_done = disinformer.step() is None
  if turn == 1 or disinformer_done:
    print("Running mitigator...")
    mitigator_done = mitigator.step() is None

  ranking_algorithm.rank()
  step_no += 1
  graph.display_graph(title="Step " + str(step_no), **display_params)
  turn = (turn + 1) % 2

graph.display_graph(title="Step " + str(step_no), **(display_params | {'auto_close': -1}))

graph.close()
