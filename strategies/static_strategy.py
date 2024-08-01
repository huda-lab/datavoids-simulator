from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from agent import Agent

from .strategy import Strategy


class StaticStrategy(Strategy):
  """
  Nodes and edges are introduced by order. The smaller the ID the earlier it is introduced.
  This makes the strategy always works the same.
  """

  def __init__(self) -> None:
    super().__init__()

  def get_strategy_name(self):
    return 'static'

  def initialize_strategy(self, agent: Agent):
    super().initialize_strategy(agent)

    # Planned edges and nodes are shuffled to make the strategy random
    self.plan_edges = self.agent.plan['edges'].copy()
    self.plan_nodes = self.agent.plan['nodes'].copy()

    # order plan edges and nodes by id
    self.plan_edges.sort()
    self.plan_nodes.sort()

    # Past nodes and edges are used to avoid planning edges that were already proposed
    # in the past, and to check which edges can be proposed
    self.past_nodes = set()
    self.past_edges = set()

  def step(self):
    super().step()

    for e in self.plan_edges:
      if e[0] not in self.past_nodes and not self.agent.graph.are_nodes_existing([e[0]]):
        continue
      if e[1] not in self.past_nodes and not self.agent.graph.are_nodes_existing([e[1]]):
        continue

      self.past_edges.add(e)
      self.plan_edges.remove(e)
      return {'nodes': [], 'edges': [e]}

    if len(self.plan_nodes) > 0:
      n = self.plan_nodes.pop(0)
      self.past_nodes.add(n)
      return {'nodes': [n], 'edges': []}

    return None
