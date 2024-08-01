import psycopg2
import matplotlib.pyplot as plt
import networkx as nx
import json
import os


class Graph:

  def __init__(self, config):
    self.config = config
    self.node_display_positions = None
    self.group_colors = config["groups_colors"]
    self.stored_functions = []

  def connect(self):
    self.conn = psycopg2.connect(**self.config["database"])
    self.cursor = self.conn.cursor()
    self.load_stored_functions()

  def close(self):
    self.cursor.close()
    self.conn.close()

  def load_stored_functions(self):
    if 'stored_functions_dir' not in self.config:
      return
    stored_functions_path = self.config['stored_functions_dir']
    for filename in os.listdir(stored_functions_path):
      if filename.endswith(".sql"):
        # open the SQL file
        with open(os.path.join(stored_functions_path, filename), 'r') as f:
          sql = f.read()
        try:
          self.cursor.execute(sql)
          self.conn.commit()
        except Exception as e:
          print(f"An error occurred when trying to execute {filename}: {e}")

  def set_group_to_nodes(self, group_name: str, where_clause: str, commit: bool = True):
    """ Sets the given group to all nodes that match the where clause. """
    self.cursor.execute("update nodes set grp = %s where " + where_clause, (group_name,))
    if commit:
      self.conn.commit()

  def set_edges_active(self, active: bool, where_clause: str, commit: bool = True):
    """ Sets all edges that match the where clause to active or inactive. """
    self.cursor.execute("update edges set active = %s where " + where_clause, (active,))
    if commit:
      self.conn.commit()

  def get_nodes_with_group(self, group, active=None, random_order=False, respect_date_added=False):
    """ Returns all nodes that have the given group. """
    if respect_date_added:
      if active is None:
        self.cursor.execute(
            "select id from nodes natural join nodes_info where grp = %s order by date_added, random()", (group,))
      else:
        self.cursor.execute(
            "select id from nodes natural join nodes_info where grp = %s and active = %s order by date_added, random()",
            (group,
             active))
    else:
      if random_order:
        if active is None:
          self.cursor.execute("select id from nodes where grp = %s order by random()", (group,))
        else:
          self.cursor.execute(
              "select id from nodes where grp = %s and active = %s order by random()", (group, active))
      else:
        if active is None:
          self.cursor.execute("select id from nodes where grp = %s", (group,))
        else:
          self.cursor.execute(
              "select id from nodes where grp = %s and active = %s", (group, active))
    return self.cursor.fetchall()

  def get_number_of_active_nodes(self):
    """ Returns the number of active nodes. """
    self.cursor.execute("select count(*) from nodes where active = true")
    return self.cursor.fetchone()[0]

  def get_nodes_ordered_by_date_added(self, group, active=None):
    """ Returns a list of active nodes as a list of ids ordered by date added. """
    if active is None:
      self.cursor.execute("""
        select
          id, date_added
        from nodes natural join nodes_info
        where
          grp = %s
          order by date_added, id desc;
      """, (group,))
    else:
      self.cursor.execute("""
        select
          id, date_added
        from nodes natural join nodes_info
        where
          grp = %s
          and active = %s
          order by date_added, id desc;
      """, (group, active))

    return self.cursor.fetchall()

  def get_nodes_ordered_by_rank(self, group, rank_field='pagerank', active=None):
    """ Returns a list of active nodes as a list of ids ordered by search rank importance. """
    if active is None:
      self.cursor.execute(f"""
        select
          id, {rank_field}
        from nodes natural join rank natural join nodes_info
        where
          grp = %s
          order by {rank_field}, id desc;
      """, (group,))
    else:
      self.cursor.execute(f"""
        select
          id, {rank_field}
        from nodes natural join rank natural join nodes_info
        where
          grp = %s
          and active = %s
          order by {rank_field}, id desc;
      """, (group, active))

    return self.cursor.fetchall()

  def get_number_of_active_edges(self):
    """ Returns the number of active edges. """
    self.cursor.execute("select count(*) from edges where active = true")
    return self.cursor.fetchone()[0]

  def get_number_of_deactivated_nodes(self):
    """ Returns the number of deactivated nodes. """
    self.cursor.execute("select count(*) from nodes where active = false")
    return self.cursor.fetchone()[0]

  def get_number_of_deactivated_edges(self):
    """ Returns the number of deactivated edges. """
    self.cursor.execute("select count(*) from edges where active = false")
    return self.cursor.fetchone()[0]

  def get_number_of_nodes_with_group(self, group):
    """ Returns the number of nodes of a certain group. """
    self.cursor.execute("select count(*) from nodes where grp = %s", group)
    return self.cursor.fetchone()[0]

  def set_active_edges_with_group(self, group, active, commit=True):
    """ Sets all edges in the given group to active or inactive (depending on the active parameter). """
    self.cursor.execute(
        """update edges set active = %s
        where des in (select id from nodes where grp = %s)
        or src in (select id from nodes where grp = %s)""", (active, group, group))
    if commit:
      self.conn.commit()

  def set_active_nodes_with_group(self, group, active, commit=True):
    """ Sets all nodes in the given group to active or inactive (depending on the active parameter). """
    self.cursor.execute("update nodes set active = %s where grp = %s", (active, group))
    if commit:
      self.conn.commit()

  def set_node_active(self, node_id, active, commit=True):
    """ Sets the node with the given id to active or inactive (depending on the active parameter). """
    self.cursor.execute("update nodes set active = %s where id = %s", (active, node_id))
    if commit:
      self.conn.commit()

  def set_edge_active(self, src, des, active, commit=True):
    """ Sets the edge (src, des) to active or inactive (depending on the active parameter). """
    self.cursor.execute(
        "update edges set active = %s where src = %s and des = %s", (active, src, des))
    if commit:
      self.conn.commit()

  def set_all_nodes_and_edges_active(self, commit=True):
    """ Sets all nodes and edges to active. """
    if self.get_number_of_deactivated_nodes() > 0:
      self.cursor.execute("update nodes set active = true where active = false")
    if self.get_number_of_deactivated_edges() > 0:
      self.cursor.execute("update edges set active = true where active = false")
    if commit:
      self.conn.commit()

  def are_nodes_existing(self, node_ids: list[int]):
    """ Checks if all nodes in the list exist and are active in the database. """
    self.cursor.execute(
        "select count(*) from nodes where id = ANY(%s) and active = true", (node_ids,))
    return self.cursor.fetchone()[0] == len(node_ids)

  def set_group_colors(self, group_colors: dict[str, str]):
    self.group_colors = group_colors

  def get_edges_with_group(self, group, active=True, random_order=False):
    """ Returns all edges that have a node in the given group as source or destination. """
    self.cursor.execute(
        """select src, des
        from edges inner join nodes src_nodes on src = src_nodes.id
        inner join nodes des_nodes on des = des_nodes.id
        where des_nodes.grp = %s or src_nodes.grp = %s
        and src_nodes.active = %s
        and des_nodes.active = %s
        and edges.active = %s
      """ + (" order by random()" if random_order else ""), (group, group, active, active, active))
    return self.cursor.fetchall()

  def get_sum_all_rank_of_a_group(self, group, active=True):
    """ Returns the sum of all ranks of a group. """
    self.cursor.execute(
        """select sum(rank.pagerank)
        from rank inner join nodes on rank.id = nodes.id
        where nodes.grp = %s and active = %s""", (group, active))
    return self.cursor.fetchone()[0]

  def get_avg_all_rank_of_a_group(self, group, active=True):
    """ Returns the avg of all ranks of a group. """
    self.cursor.execute(
        """select avg(rank.pagerank)
        from rank inner join nodes on rank.id = nodes.id
        where nodes.grp = %s and active = %s""", (group, active))
    return self.cursor.fetchone()[0]

  def get_max_rank_of_a_group(self, group, active=True):
    """ Returns the max of all ranks of a group. """
    self.cursor.execute(
        """select max(rank.pagerank)
        from rank inner join nodes on rank.id = nodes.id
        where nodes.grp = %s and active = %s""", (group, active))
    return self.cursor.fetchone()[0]

  def get_id_of_max_rank_of_a_group(self, group, active=True):
    """ Returns the max of all ranks of a group. """
    self.cursor.execute(
        """select id, rank
        from nodes natural join rank
        where grp = %s
        and active = %s
        order by rank desc
        limit 1;""", (group, active))
    res = self.cursor.fetchone()
    return res[0] if res else None

  def sort_nodes_containing_keyword_first(self, nodes, keyword):
    nodes_containing_keywords = []
    nodes_not_containing_keywords = []
    for n in nodes:
      self.cursor.execute("""
        select count(*)
        from nodes_info
        where id = %s and content_vector @@ to_tsquery(%s);
      """, (n, keyword))
      if self.cursor.fetchone()[0] > 0:
        nodes_containing_keywords.append(n)
      else:
        nodes_not_containing_keywords.append(n)
    return nodes_containing_keywords + nodes_not_containing_keywords

  def get_top_k(self, k, groups=None, active=True):
    """ Returns the top n nodes considering the current ranking
        with also the group they belong to.
    """
    self.cursor.execute("""
      select id, grp, searchrank
      from nodes natural join rank
      where grp = ANY(%s)
      and active = %s
      and grp is not NULL
      order by searchrank desc
      limit %s;
    """, (groups, active, k))

    res = []
    for row in self.cursor.fetchall():
      res.append({
          'id': row[0],
          'group': row[1] if row[1] is not None else 'None',
          'rank': row[2]
      })
    return res

  def get_min_rank_of_a_group(self, group, active=True):
    """ Returns the min of all ranks of a group. """
    self.cursor.execute(
        """select min(rank.pagerank)
        from rank inner join nodes on rank.id = nodes.id
        where nodes.grp = %s and active = %s""", (group, active))
    return self.cursor.fetchone()[0]

  def get_node_ranking(self, node_id):
    """ Returns the rank of the given node. """
    self.cursor.execute("select searchrank from rank where id = %s", (node_id,))
    if self.cursor.rowcount == 0:
      return 0
    return self.cursor.fetchone()[0]

  def get_groups(self):
    """ Returns all groups that are in the database. """
    self.cursor.execute("select distinct grp from nodes")
    return [r[0] for r in self.cursor.fetchall()]

  def calculate_node_display_positions(self, fn=nx.circular_layout, min_max_pos=[0.2, 0.8]):
    """
    Calculates the positions of the nodes for the display_graph function.
    This is to have a consistent display of the graph overtime.
    """
    G = nx.DiGraph()
    self.cursor.execute("select id, grp, active from nodes order by id")
    for node in self.cursor.fetchall():
      G.add_node(node[0])
    self.cursor.execute("select src, des from edges order by src, des")
    edges = self.cursor.fetchall()
    for edge in edges:
      G.add_edge(edge[0], edge[1])
    # self.node_display_positions = fn(G)

    node_positions = fn(G)

    x_coords = [pos[0] for pos in node_positions.values()]
    y_coords = [pos[1] for pos in node_positions.values()]
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    # Normalize positions to be within the range [new_min, new_max]
    for node, pos in node_positions.items():
      x, y = pos
      x_new = (x - x_min) / (x_max - x_min) * (min_max_pos[1] - min_max_pos[0]) + min_max_pos[0]
      y_new = (y - y_min) / (y_max - y_min) * (min_max_pos[1] - min_max_pos[0]) + min_max_pos[0]
      node_positions[node] = [x_new, y_new]

    self.node_display_positions = node_positions

  def display_graph(self, rank=True,
                    title=None,
                    auto_close=1,
                    node_size=500,
                    font_size=8,
                    fig_size=(5, 5),
                    edge_width=1,
                    with_labels=True,
                    layout=nx.circular_layout
                    ):
    """ Displays the graph in a matplotlib window. """

    G = nx.DiGraph()

    # adding colors
    groups = self.get_groups()
    group_colors = {}
    for i, group in enumerate(groups):
      if group in self.group_colors:
        group_colors[group] = self.group_colors[group]
      else:
        group_colors[group] = plt.cm.tab10(7)

    # adding nodes
    if rank:
      self.cursor.execute("""
        select id, row_number() over (order by rank.pagerank desc), rank.pagerank
        from nodes natural join rank
        where active = true;
      """)
      node_rank_pos = {}
      for node in self.cursor.fetchall():
        node_rank_pos[node[0]] = node[1]

    self.cursor.execute("select id, grp, active from nodes order by id")
    labels = {}
    nodes_colors = []
    for node in self.cursor.fetchall():
      G.add_node(node[0])
      if rank and node[2]:
        labels[node[0]] = f'{node[0]}\n#{node_rank_pos[node[0]]}'
      else:
        labels[node[0]] = f'{node[0]}'
      nodes_colors.append(group_colors[node[1]] if node[2] else (0, 0, 0, 0.1))

    # adding edges
    self.cursor.execute("select src, des, active from edges order by src, des")
    edges = self.cursor.fetchall()
    edges = filter(lambda e: e[0] in labels and e[1] in labels, edges)
    for edge in edges:
      G.add_edge(edge[0], edge[1], color="#C4DCC9" if edge[2] else (0, 0, 0, 0.1))

    # nodes positions
    if self.node_display_positions is None:
      self.calculate_node_display_positions(fn=layout)
    # find the max y and x and min x and y of all nodes
    max_y = max(self.node_display_positions.values(), key=lambda x: x[1])[1]
    min_y = min(self.node_display_positions.values(), key=lambda x: x[1])[1]
    max_x = max(self.node_display_positions.values(), key=lambda x: x[0])[0]
    min_x = min(self.node_display_positions.values(), key=lambda x: x[0])[0]
    print("max_y:", max_y, "min_y:", min_y, "max_x:", max_x, "min_x:", min_x)

    # distinguishing the target nodes from the rest
    target_nodes_ids = list(self.config['target_node'].values())
    node_sizes = [100 if node[0] in target_nodes_ids else node_size for node in G.nodes(data=True)]
    self.node_display_positions[target_nodes_ids[0]] = (0.05, 0.05)
    self.node_display_positions[target_nodes_ids[1]] = (0.95, 0.95)

    # drawing graph
    print("drawing graph...")
    plt.figure(figsize=fig_size)
    if title:
      ax = plt.gca()
      ax.set_title(title)
    nx.draw(
        G,
        connectionstyle="arc3, rad = 0.1",
        pos=self.node_display_positions,
        with_labels=with_labels,
        labels=labels,
        font_color='#666666',
        node_size=node_sizes,
        font_size=font_size,
        width=edge_width,
        node_color=nodes_colors,
        edge_color=[G[u][v]['color'] for u, v in G.edges()]
    )

    if auto_close > 0:
      plt.show(block=False)
      plt.pause(auto_close)
      plt.close("all")
    else:
      plt.show()
