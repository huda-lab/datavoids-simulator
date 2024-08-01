from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph

from labeler.batch_labeler import BatchLabeler


class BatchLabelerKeywordsOnly(BatchLabeler):

  def lbl(self, graph: Graph):
    graph.cursor.callproc("contains_word_labeler", [[self.grp1_keywords], self.grp1_label])
    graph.conn.commit()
    graph.cursor.callproc("contains_word_labeler", [[self.grp2_keywords], self.grp2_label])
    graph.conn.commit()
