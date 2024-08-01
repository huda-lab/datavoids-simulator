from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class NeighborhoodExpansionStrategy(Strategy):
  """
  This strategy is similar to the random strategy, but it tries to expand the
  neighborhood of what is already in the graph. It will first try to add nodes, then edges.

  If datavoids are specified, this strategy is going to try to add the page that contain that
  these words first.
  """

  def __init__(self, focus_node=None) -> None:
    super().__init__(focus_node)

  def get_strategy_name(self):
    return 'neighexp'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()
    self.past_nodes = set()
    self.past_edges = set()

    # Edges from plan_nodes that are belonging to nodes that are existing
    # This is just for speeding up things
    self.plan_edges_between_existing_nodes = []
    self.update_plan_edges_between_existing_nodes()

  def update_plan_edges_between_existing_nodes(self):
    currently_active_nodes_ids = self.agent.graph.get_nodes_with_group(
      self.agent.group, active=True)
    currently_active_nodes_ids.update(self.past_nodes)
    self.plan_edges_between_existing_nodes = [
        (s, d) for (s, d) in self.plan_edges
        if s in currently_active_nodes_ids and d in currently_active_nodes_ids
    ]

  def step(self):
    super().step()

    if self.focus_node is not None and self.focus_node not in self.past_nodes and self.focus_node in self.plan_nodes:
      self.past_nodes.add(self.focus_node)
      self.plan_nodes.remove(self.focus_node)
      self.update_plan_edges_between_existing_nodes()
      return {'nodes': [self.focus_node], 'edges': []}

    if len(self.plan_edges_between_existing_nodes) > 0:
      e = random.choice(self.plan_edges_between_existing_nodes)
      self.past_edges.add(e)
      self.plan_edges.remove(e)
      self.plan_edges_between_existing_nodes.remove(e)
      return {'nodes': [], 'edges': [e]}

    # searching for a node that is connected to a node in the past
    for n in self.plan_nodes:
      for e in self.past_edges:
        if e[0] == n or e[1] == n:
          self.past_nodes.add(n)
          self.plan_nodes.remove(n)
          self.update_plan_edges_between_existing_nodes()
          return {'nodes': [n], 'edges': []}

    # return a random node
    if len(self.plan_nodes) > 0:
      n = self.plan_nodes.pop(0)
      self.past_nodes.add(n)
      self.update_plan_edges_between_existing_nodes()
      return {'nodes': [n], 'edges': []}

    return None
