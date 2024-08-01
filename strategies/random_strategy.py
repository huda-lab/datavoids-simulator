from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class RandomStrategy(Strategy):
  """
  The random strategy plans the nodes and edges to add at first.
  At each step it performs a random choice among edges that are connecting existing nodes.
  If there are no more existing edges to add it will proceed adding a random node.
  """

  def __init__(self, seed=None) -> None:
    super().__init__()
    self.seed = seed

  def get_strategy_name(self):
    return 'rnd'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    if self.seed is not None:
      self.rnd = random.Random(self.seed)
    else:
      self.rnd = random.Random()

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()

    if self.seed is not None:
      # order plan edges and nodes by id
      self.plan_edges.sort()
      self.plan_nodes.sort()

    # Past nodes and edges are used to avoid planning edges that were already proposed
    # in the past, and to check which edges can be proposed
    self.past_nodes = set()
    self.past_edges = set()

    # Edges from plan_nodes that are belonging to nodes that are existing
    # This is just for speeding up things
    self.plan_edges_between_existing_nodes = []
    self.update_plan_edges_between_existing_nodes()

  def update_plan_edges_between_existing_nodes(self):
    currently_active_nodes_ids = set(
        self.agent.graph.get_nodes_with_group(
            self.agent.group, active=True))
    currently_active_nodes_ids.update(self.past_nodes)
    self.plan_edges_between_existing_nodes = [
      (s, d) for (s, d) in self.plan_edges
      if s in currently_active_nodes_ids and d in currently_active_nodes_ids
    ]

  def step(self):
    super().step()

    # if there are edges to add in the existing nodes, this is always done first
    if len(self.plan_edges_between_existing_nodes) > 0:
      e = self.rnd.choice(self.plan_edges_between_existing_nodes)
      self.past_edges.add(e)
      self.plan_edges.remove(e)
      self.plan_edges_between_existing_nodes.remove(e)
      return {'nodes': [], 'edges': [e]}

    # return a random node
    if len(self.plan_nodes) > 0:
      if self.seed is not None:
        n = self.rnd.choice(self.plan_nodes)
        self.plan_nodes.remove(n)
      else:
        n = self.plan_nodes.pop(0)
      self.past_nodes.add(n)
      self.update_plan_edges_between_existing_nodes()
      return {'nodes': [n], 'edges': []}

    return None
