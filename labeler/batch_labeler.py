from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph

import random


class BatchLabeler:

  def __init__(self, label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id):
    self.label = label
    self.grp1_label, self.grp2_label = label.split("_")
    self.topic = topic
    self.grp1_keywords = grp1_keywords
    self.grp2_keywords = grp2_keywords
    self.grp1_page_id = grp1_page_id
    self.grp2_page_id = grp2_page_id

  def lbl(self, graph: Graph):
    return self.grp1_label if random.random() < 0.5 else self.grp2_label
