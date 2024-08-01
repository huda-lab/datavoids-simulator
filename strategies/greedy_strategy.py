from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

import random
from .strategy import Strategy


class GreedyStrategy(Strategy):
  """
  It searches for an edge to add to the plan, and adds it.

  If no edge is available (meaning the edges are pointing to non-existing pages), then
  the page with the highest rank is added.

  The rank is approximated as the ranking of the only nodes that are in the plan, since
  these are the only realistically available nodes.
  """

  def __init__(self, reverse=True) -> None:
    super().__init__()
    self.reverse = reverse

  def get_strategy_name(self):
    return 'greedy'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()

    ordered_nodes = self.agent.graph.get_nodes_ordered_by_rank(self.agent.group)
    order_dict = dict(ordered_nodes)
    self.plan_nodes.sort(key=lambda x: order_dict[x], reverse=self.reverse)

    random.shuffle(self.plan_edges)

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

    # trying to add edges (we search through the past nodes just in case we already
    # proposed an edge or node that was not committed yet)
    # for e in self.plan_edges_between_existing_nodes:
    if len(self.plan_edges_between_existing_nodes) > 0:
      e = random.choice(self.plan_edges_between_existing_nodes)
      self.past_edges.add(e)
      self.plan_edges.remove(e)
      self.plan_edges_between_existing_nodes.remove(e)
      return {'nodes': [], 'edges': [e]}

    # return a node
    if len(self.plan_nodes) > 0:
      n = self.plan_nodes.pop(0)
      self.past_nodes.add(n)
      self.update_plan_edges_between_existing_nodes()
      return {'nodes': [n], 'edges': []}

    return None
