import subprocess
import shlex
import time
import copy
import psycopg2

from graph import Graph


def run_sql(connection, script):
  with connection.cursor() as cursor:
    cursor.execute(script)
    connection.commit()
    time.sleep(1)


def run_bash(commands):
  for command in commands:
    subprocess.run(shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)


def prepare_lite_db(config,
                    lite_db_name,
                    prob_node_inserted_if_not_important=0.05,
                    prob_edge_inserted_if_not_important=0.05):

  graph = Graph(config)
  graph.connect()

  print("Creating important pages")
  run_sql(graph.conn, """
  create table if not exists important_nodes (id int primary key);
  delete from important_nodes;
  insert into important_nodes (select distinct id from nodes where grp is not null);
  """)

  with graph.conn.cursor() as cursor:
    cursor.execute("select count(*) from important_nodes")
    print("Important pages:", cursor.fetchone()[0])

  print("Dumping important pages")
  run_bash([
      "rm -f data/important_nodes.sql",
      "pg_dump -U postgres -d {} -t important_nodes -f data/important_nodes.sql".format(
        config["database"]["database"])
  ])

  print("Dumping idf table")
  run_bash([
      "rm -f data/idf_values_seeds_nodes.sql",
      "pg_dump -U postgres -d {} -t idf_values_seeds_nodes -f data/idf_values_seeds_nodes.sql".format(
        config["database"]["database"])
  ])

  print("Creating important edges")
  run_sql(graph.conn, """
    create table if not exists important_edges (src int, des int);
    delete from important_edges;
    insert into important_edges (src, des)
    select src, des from edges
    where src in (
      select id from nodes where grp is not null
    ) and des in (
      select id from nodes where grp is not null
    );
  """)

  with graph.conn.cursor() as cursor:
    cursor.execute("select count(*) from important_edges")
    print("Important edges:", cursor.fetchone()[0])

  print("Dumping important edges")
  run_bash([
      "rm -f data/important_edges.sql",
      "pg_dump -U postgres -d {} -t important_edges -f data/important_edges.sql".format(
        config["database"]["database"])
  ])

  graph.close()

  print("Connecting to lite DB")
  wikilite_config = copy.deepcopy(config)
  wikilite_config["database"]["database"] = lite_db_name
  graph = Graph(wikilite_config)
  graph.connect()

  print("Dropping old tables")
  run_sql(graph.conn, """
    drop table if exists important_nodes;
    drop table if exists important_edges;
  """)

  print("Importing important pages and edges")
  run_bash([
      "psql -U postgres -d {} -f data/important_nodes.sql".format(lite_db_name),
      "psql -U postgres -d {} -f data/important_edges.sql".format(lite_db_name)
  ])

  print("Importing idf")
  run_bash([
      "psql -U postgres -d {} -f data/idf_values_seeds_nodes.sql".format(lite_db_name),
  ])

  # If original_nodes doesn't exist we need to create it with the current nodes
  with graph.conn.cursor() as cursor:
    cursor.execute("""
        select exists (
          select from information_schema.tables
          where table_name = 'original_nodes'
        )
      """)
    if not cursor.fetchone()[0]:
      print("Creating original_nodes and nodes")
      run_sql(graph.conn, """
        alter table nodes rename to original_nodes;
        create table nodes (like original_nodes);
        alter table nodes add primary key (id);
        alter table nodes_info drop constraint if exists nodes_info_id_fkey;
        create index idx_nodes_id on nodes (id);
      """)

    cursor.execute("""
      select exists (
        select from information_schema.tables
        where table_name = 'original_edges'
      )
    """)
    if not cursor.fetchone()[0]:
      print("Creating original_edges and edges")
      run_sql(graph.conn, """
        alter table edges rename to original_edges;
        create table edges (like original_edges);
        alter table edges add primary key (src, des),
              add foreign key (src) references nodes(id),
              add foreign key (des) references nodes(id);
        create index idx_original_edges_src on original_edges (src);
        create index idx_original_edges_des on original_edges (des);
        create index idx_important_edges_src on important_edges (src);
        create index idx_important_edges_des on important_edges (des);
      """)

  print("Deleting edges and nodes tables, emptying rank")
  run_sql(graph.conn, """
    delete from edges;
    delete from nodes;
  """)

  print("Creating nodes")
  run_sql(graph.conn, """
    insert into nodes (id, grp, active) select id, grp, active
    from original_nodes
    where (random() < {prob_node_inserted_if_not_important}) or (
      exists (select 1 from important_nodes where id = original_nodes.id)
    ) or (
      id = {target_node_0} or id = {target_node_1}
    );
  """.format(
      target_node_0=list(config['target_node'].values())[0],
      target_node_1=list(config['target_node'].values())[1],
      prob_node_inserted_if_not_important=prob_node_inserted_if_not_important,
  ))
  print("Creating edges")
  run_sql(graph.conn, """
    insert into edges (src, des, active)
    (
      select e.src, e.des, e.active
      from original_edges e
      join nodes src_nodes on e.src = src_nodes.id
      join nodes des_nodes on e.des = des_nodes.id
      where random() < {prob_edge_inserted_if_not_important} or (
        exists (select 1 from important_edges ie where ie.src = e.src)
        and exists (select 1 from important_edges ie where ie.des = e.des)
      )
    );
  """.format(
      prob_edge_inserted_if_not_important=prob_edge_inserted_if_not_important,
  ))

  print("Counting")
  # print number of nodes and edges
  with graph.conn.cursor() as cursor:
    cursor.execute("select count(*) from nodes")
    print("Nodes:", cursor.fetchone()[0])
    cursor.execute("select count(*) from edges")
    print("Edges:", cursor.fetchone()[0])

  graph.close()
  print("Done")
