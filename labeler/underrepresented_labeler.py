from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph

from labeler.generic_labeler import GenericLabeler


class UnderrepresentedTieLabeler(GenericLabeler):
  '''
     It gives the label of the more underrepresented group
  '''

  def __init__(self, label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id):
    super().__init__(label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id)

  def lbl(self, graph, article_title, article_extract):
    grp1_no = graph.get_nodes_with_group(self.grp1_label)
    grp2_no = graph.get_nodes_with_group(self.grp2_label)

    return self.grp1_label if len(grp1_no) < len(grp2_no) else self.grp2_label
