from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from graph import Graph


class Rank:

  def __init__(self, graph: Graph, rank_algorithm: str):
    """ The rank algorithm is a stored procedure in the database and
    it is loaded from a file with the same name as the rank_algorithm parameter."""
    self.graph = graph
    self.rank_algorithm = rank_algorithm

  def rank(self, keyword, delete_pagerank=False, delete_tsrank=False):
    """run the rank() stored procedure in the database"""
    try:
      to_rank = False

      if delete_pagerank:
        print("deleting all rank data...")
        self.graph.cursor.execute("delete from rank")
        self.graph.conn.commit()
        to_rank = True
      elif delete_tsrank:
        to_rank = True
      else:
        # checking if ranking is out of date
        self.graph.cursor.execute("select prop from info where id = 'rank_by_keyword'")
        res = self.graph.cursor.fetchone()
        if res is None:
          to_rank = True
          self.graph.cursor.execute(
              "insert into info(id, prop) values('rank_by_keyword', %s)", (keyword,))
          self.graph.conn.commit()
        elif res[0] != keyword:
          to_rank = True
          self.graph.cursor.execute(
              "update info set prop = %s where id = 'rank_by_keyword'", (keyword,))
          self.graph.conn.commit()

      if to_rank:
        print("deleting rank data...")
        # check if tsrank column exists
        self.graph.cursor.execute("""
            select column_name
            from information_schema.columns
            where
              table_name = 'rank' and
              column_name = 'tsrank'
        """)
        res = self.graph.cursor.fetchone()
        if res is not None:
          self.graph.cursor.execute("update rank set tsrank = NULL, searchrank = NULL")
          self.graph.conn.commit()

        print("ranking...")
        self.graph.cursor.callproc(self.rank_algorithm, (keyword,))
        self.graph.conn.commit()

      for notice in self.graph.conn.notices:
        print(notice, end='')

    except Exception as e:
      print("ERROR:", e)
      return None

  def print_top_10(self):
    self.graph.cursor.execute("select id, rank from nodes order by rank desc limit 10")
    for row in self.graph.cursor.fetchall():
      print(row)
