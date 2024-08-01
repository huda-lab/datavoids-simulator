from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph

from labeler.batch_labeler import BatchLabeler


class BatchLabelerByLinks(BatchLabeler):

  def __init__(self, label, topic, grp1_keywords, grp2_keywords,
               grp1_page_id, grp2_page_id, max_hops):
    super().__init__(label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id)
    self.max_hops = max_hops

  def lbl(self, graph: Graph, reset_labels=False):
    if reset_labels:
      graph.cursor.execute("update nodes set grp = null where grp is not null")
      graph.conn.commit()

    graph.cursor.callproc("set_group_from_target_page", [
        self.grp1_page_id, self.grp1_label, self.max_hops
    ])
    graph.cursor.callproc("set_group_from_target_page", [
        self.grp2_page_id, self.grp2_label, self.max_hops
    ])
    graph.cursor.execute(
        "update nodes set grp = %s where id = %s;",
        (self.grp1_label, self.grp1_page_id))
    graph.cursor.execute(
        "update nodes set grp = %s where id = %s;",
        (self.grp2_label, self.grp2_page_id))

    graph.conn.commit()
