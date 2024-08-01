from graph import Graph
from labeler.underrepresented_labeler import UnderrepresentedTieLabeler
from labeler.batch_by_links_labeler import BatchLabelerByLinks
from labeler.labeler_commons import sanitize_extracted_text, ENGLISH_WORD_AVG_CHARACTERS_LENGTH, load_keywords_dataset
import sys
import json


def label_groups_on_keywords_only(label, labels_dataset, graph):
  print("Labeling keyword: " + label + " (" + labels_dataset[label]["desc"] + ")")
  grp1_label, grp2_label = label.split("_")
  grp1_keywords = labels_dataset[label][grp1_label]
  grp2_keywords = labels_dataset[label][grp2_label]

  graph.cursor.callproc("contains_word_labeler", [[grp1_keywords], grp1_label])
  graph.conn.commit()
  graph.cursor.callproc("contains_word_labeler", [[grp2_keywords], grp2_label])
  graph.conn.commit()


def label_groups_on_keywords_and_external_labeler(label, labels_dataset, lookup_words, graph):
  grp1_label, grp2_label = label.split("_")
  grps_label = label.replace("_", "|")
  lookup_chrs = lookup_words * 2 * ENGLISH_WORD_AVG_CHARACTERS_LENGTH
  print(f"Labeling keyword: {label} ({labels_dataset[label]['desc']}) (grp = {grps_label})")
  keywords = labels_dataset[label][grp1_label] + labels_dataset[label][grp2_label]

  graph.cursor.callproc("contains_word_labeler", [[keywords], grps_label])
  graph.conn.commit()
  graph.cursor.execute("""
    select
        id, grp,
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
        id
  """, (lookup_chrs, lookup_chrs, keywords))

  for i in range(10):
    res = graph.cursor.fetchone()
    res_id = res[0]
    res_grp = res[1]
    res_text = sanitize_extracted_text(res[2])
    print(f"ID: {res_id} - {res_grp} - {res_text}")


def display_groups_count(graph, print_null_group=False):
  # print all groups number
  graph.cursor.execute("""
    select grp, count(*) from nodes group by grp order by count(*) desc
  """)
  print("Groups count:")
  for res in graph.cursor.fetchall():
    if not print_null_group and res[0] is None:
      continue
    print(" ", (res[0] if res[0] is not None else 'None') + ":", res[1])


def get_groups_count(graph):
  graph.cursor.execute("""
    select grp, count(*) from nodes group by grp order by count(*) desc
  """)
  groups_count = {}
  for res in graph.cursor.fetchall():
    groups_count[res[0] if res[0] is not None else 'None'] = res[1]
  return groups_count


def label_db_with_links(graph, config, max_hops=1, reset_labels=True):
  grp1_label = config["mitigator_keyword"]
  grp2_label = config["disinformer_keyword"]
  label = grp1_label + "_" + grp2_label

  print("Labeling", grp1_label, "/", grp2_label)
  print(" Target nodes:", config["target_node"][grp1_label], config["target_node"][grp2_label])

  batch_labeler = BatchLabelerByLinks(
      label,
      f"{grp1_label} vs. {grp2_label}",
      config[grp1_label + "_keywords"],
      config[grp2_label + "_keywords"],
      config["target_node"][grp1_label],
      config["target_node"][grp2_label],
      max_hops
  )

  batch_labeler.lbl(graph, reset_labels=reset_labels)


def remove_multi_labeled_nodes(graph, display_groups=False):
  graph.cursor.execute("""
    update nodes set grp = null where grp like '%|%'
  """)
  graph.conn.commit()

  if display_groups:
    display_groups_count(graph)


def assign_multilabeled_nodes_to_underrepresented(graph, config):
  grp1_label = config["mitigator_keyword"]
  grp2_label = config["disinformer_keyword"]
  label = grp1_label + "_" + grp2_label

  tie_labeler = UnderrepresentedTieLabeler(
      label,
      f"{grp1_label} vs. {grp2_label}",
      config[grp1_label + "_keywords"],
      config[grp2_label + "_keywords"],
      config["target_node"][grp1_label],
      config["target_node"][grp2_label]
  )

  graph.cursor.execute("""
    select id, url, content from nodes natural join nodes_info where grp = %s
  """, (grp1_label + "|" + grp2_label,))
  for res in graph.cursor.fetchall():
    res_id = res[0]
    res_url = res[1]
    res_title = res_url.split("/")[-1].replace("_", " ")
    res_content = res[2]
    new_grp = tie_labeler.lbl(graph, res_title, res_content)
    graph.cursor.execute("""
      update nodes set grp = %s where id = %s
    """, (new_grp, res_id))
  graph.conn.commit()


def label_database(config, display_groups=True, reset_active_status=True,
                   filter_by_topk_words=3, skip_labeling=False, remove_multilabeled_nodes=True):
  """
    filter_by_topk_words to filter the groups to only those that have one of the topk words, as
    ranked by tf-idf, in the seeds pages content. If this value is 0 the pages are not filtered
  """
  graph = Graph(config)
  graph.connect()

  print("Labeling started")
  if reset_active_status:
    graph.cursor.execute("update nodes set active = true where active = false")
    graph.cursor.execute("update edges set active = true where active = false")

  if not skip_labeling:
    label_db_with_links(graph, config, config["labeling_hops"])

  graph.conn.commit()

  if display_groups:
    display_groups_count(graph)

  if filter_by_topk_words > 0:
    grp1_label = config["mitigator_keyword"]
    grp2_label = config["disinformer_keyword"]
    graph.cursor.execute(
      "select ungroup_nodes_with_no_topk_words(array[%s, %s]::integer[], array[%s, %s]::text[], %s::integer)",
      (
        config["target_node"][grp1_label],
        config["target_node"][grp2_label],
        grp1_label,
        grp2_label,
        filter_by_topk_words
      )
    )
    graph.conn.commit()

  if remove_multilabeled_nodes:
    remove_multi_labeled_nodes(graph)

  if display_groups:
    display_groups_count(graph)

  groups_count = get_groups_count(graph)
  print("Done")
  graph.close()
  return groups_count


if __name__ == "__main__":
  config_file_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
  config = None
  with open(config_file_path) as config_file:
    config = json.load(config_file)

  label_database(config)
