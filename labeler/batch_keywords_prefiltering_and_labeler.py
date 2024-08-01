from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph

from labeler.batch_labeler import BatchLabeler
from labeler.labeler_commons import ENGLISH_WORD_AVG_CHARACTERS_LENGTH, sanitize_extracted_text


class BatchKeywordsPreFilteringAndLabeler(BatchLabeler):

  def __init__(self, label, topic, grp1_keywords, grp2_keywords,
               grp1_page_id, grp2_page_id, lookup_words, labeler):
    super().__init__(label, topic, grp1_keywords, grp2_keywords, grp1_page_id, grp2_page_id)
    self.lookup_words = lookup_words
    self.labeler = labeler

  def lbl(self, graph: Graph):
    grps_label = self.label.replace("_", "|")
    lookup_chrs = self.lookup_words * 2 * ENGLISH_WORD_AVG_CHARACTERS_LENGTH
    keywords = self.grp1_keywords + self.grp2_keywords

    graph.cursor.callproc("contains_word_labeler", [[keywords], grps_label])
    graph.conn.commit()
    graph.cursor.execute("""
      select
          id, url,
          string_agg(
            substring(
              content,
              greatest(1, position(word in content) - %s),
              least(length(word) + %s, length(content))
            ),
            ' [...] '
          ) as surrounding_text
      from
          nodes natural join nodes_info,
          unnest(%s) as word
      where
          content like concat('%%', word, '%%')
      group by
          id, url
    """, (lookup_chrs, lookup_chrs, keywords))

    for _ in range(10):
      res = graph.cursor.fetchone()
      res_id = res[0]
      res_title = res[1]
      res_text = sanitize_extracted_text(res[2])
      labeler_label = self.labeler.lbl(graph, res_title, res_text)
      print(f"ID: {res_id} - {res_title} - {labeler_label} - {res_text}")
