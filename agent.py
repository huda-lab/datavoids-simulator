from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph
  from strategies import Strategy

from strategies.random_strategy import RandomStrategy
import math


class Agent:

  def __init__(self, graph: Graph, group: str, config) -> None:
    """
    Args:
      graph (Graph): The graph to be labeled
      group (str): The group of nodes that the agent is responsible for
      config: simulation configuration
    """
    self.graph = graph
    self.config = config
    self.group = group
    self.steps_count = 0  # number of steps since the start
    self.cost = 0
    self.costs = self.config['costs']
    self.nodes_added = 0
    self.edges_added = 0
    self.steps_config = config['steps_config'] if 'steps_config' in config else {}
    self.step_on_each_node = self.steps_config['on_each_node'] if 'on_each_node' in self.steps_config else False
    self.step_on_each_edge = self.steps_config['on_each_edge'] if 'on_each_edge' in self.steps_config else False
    self.max_atomic_steps = self.steps_config['max_atomic_steps'] if 'max_atomic_steps' in self.steps_config else -1
    self.max_steps = self.steps_config['max_steps'] if 'max_steps' in self.steps_config else -1
    # atomic step is for example adding a node, a step can have multiple atomic steps
    self.atomic_steps_per_step = -1
    self.atomic_steps_count = 0
    self.atomic_nodes_steps_count = 0
    self.atomic_edges_steps_count = 0

    # Plan saves possible nodes and edges to be added (These are IDs for
    # nodes, and couples of (ID, ID) for edges
    self.plan = {'nodes': [], 'edges': []}
    self.executed_plan = {'nodes': [], 'edges': []}

    self.strategy = RandomStrategy()
    self.initialized = False

  def initialize_plan(self, respect_date_added=False):
    print('initialize plan')

    nodes = self.graph.get_nodes_with_group(
        self.group, random_order=True, respect_date_added=respect_date_added)
    for id in nodes:
      self.plan['nodes'].append(id[0])

    edges = self.graph.get_edges_with_group(self.group, active=False, random_order=True)
    for e in edges:
      self.plan['edges'].append(e)

    self.graph.set_active_edges_with_group(self.group, False)
    self.graph.set_active_nodes_with_group(self.group, False)

    number_of_atomic_steps = len(self.plan['nodes']) + len(self.plan['edges'])

    if self.max_atomic_steps != -1:
      if number_of_atomic_steps > self.max_atomic_steps:
        if number_of_atomic_steps % self.max_atomic_steps == 0:
          self.atomic_steps_per_step = number_of_atomic_steps // self.max_atomic_steps
        else:
          self.atomic_steps_per_step = number_of_atomic_steps // (self.max_atomic_steps - 1)

    self.strategy.initialize_strategy(self)

    self.initialized = True

  def set_strategy(self, strategy: Strategy):
    self.strategy = strategy

  def cost_insert_node(self, page_rank):
    cost = math.exp(page_rank)
    return cost

  def atomic_step(self):
    # get a node from the plan according to a strategy
    res = self.strategy.step()
    if res is None:  # the strategy ended
      return None

    for node_id in res['nodes']:
      self.atomic_nodes_steps_count += 1
      if node_id == -1:  # the strategy passes
        continue
      cost = self.cost_insert_node(self.graph.get_node_ranking(node_id))
      if self.costs["budget"] > 0 and self.cost + cost > self.costs["budget"]:
        return None
      self.nodes_added += 1
      self.graph.set_node_active(node_id, True, commit=False)
      self.cost += cost

    for edge in res['edges']:
      self.atomic_edges_steps_count += 1
      if edge[0] == -1 and edge[0] == -1:  # the strategy passes
        continue
      self.edges_added += 1
      self.graph.set_edge_active(edge[0], edge[1], True, commit=False)

    self.graph.conn.commit()

    return res

  def atomic_steps_done(self, last_res):
    if self.atomic_steps_count == 0:
      return False

    if last_res is None or \
       (self.atomic_steps_per_step > 0 and self.atomic_steps_count > self.atomic_steps_per_step) or \
       (self.step_on_each_edge and self.atomic_edges_steps_count > 0) or \
       (self.step_on_each_node and self.atomic_nodes_steps_count > 0) or \
       (self.costs["budget"] > 0 and self.cost >= self.costs["budget"]):
      return True

    return False

  def step(self):
    if not self.initialized:
      raise Exception("Agent not initialized")

    if self.costs["budget"] > 0 and self.cost >= self.costs["budget"]:
      print("budget over", self.group)
      return None

    self.steps_count += 1

    if self.max_steps > 0 and self.steps_count > self.max_steps:
      return None

    res = None
    self.atomic_steps_count = 0
    self.atomic_nodes_steps_count = 0
    self.atomic_edges_steps_count = 0
    while not self.atomic_steps_done(res):
      res = self.atomic_step()
      self.atomic_steps_count += 1

    return res
