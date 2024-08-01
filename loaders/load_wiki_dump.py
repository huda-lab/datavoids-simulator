import bz2
import os
import sys
import re
from io import StringIO
import psycopg2
import json
from lxml import etree
from loaders.wikiextractor.wikiextractor.clean import clean_markup

config = None
with open('config.json') as config_file:
  config = json.load(config_file)

inner_link_re = re.compile('\\[\\[')
link_re = re.compile('\\[\\[[^()]+?\\]\\]')
pages_number = 0
namespace_uri = "http://www.mediawiki.org/xml/export-0.10/"
ns_map = {'mw': namespace_uri}


# #TODO
# It would need more work with specifications here
# https://en.wikipedia.org/wiki/Help:Link
# Alternatively wikiextractor?
def page_title_to_link(title):
  title = title.replace(',', ' ').replace(' ', '_').lower()
  title = title.replace('\n', '').replace('\r', '')
  return title


def link_to_page_title(link):
  link = link.replace('_', ' ').title()
  return link


def get_link_content(link_raw_text):
  link_content = None
  m = inner_link_re.search(link_raw_text, 2)
  if m is None:
    link_content = link_raw_text[2:-2]
  else:
    link_content = link_raw_text[m.start() + 2:-2]
  # Take only the second part if the link is in the form [[link label|link]]
  if '|' in link_content:
    link_content = link_content.split('|')[1]
  link_content = link_content.replace('[a-zA-Z]+:', '')
  link_content = link_content.replace(' ', '_')
  # Any link here can be used in the URL https://en.wikipedia.org/wiki/ + link_content
  # Some can be redirected TODO
  return link_content


def find_links(text):
  links = []
  cur = 0
  while True:
    m = link_re.search(text, cur)
    if not m:
      break
    cur = m.end()
    links.append(get_link_content(m.group()))
  return links


def process_redirects(wiki_file_path, conn, cursor):
  with bz2.open(wiki_file_path, mode='rb') as dump_file:
    context = etree.iterparse(dump_file, events=("end",), tag="{" + namespace_uri + "}page")

    for event, element in context:
      if event == "end":
        namespace = element.findtext("mw:ns", namespaces=ns_map)
        if namespace != "0":
          continue

        from_title = element.findtext("mw:title", namespaces=ns_map)

        redirect_element = element.find("mw:redirect", namespaces=ns_map)
        if redirect_element is not None:
          to_title = redirect_element.get("title")
          # print("Redirect:", from_title, "->", to_title)
          cursor.execute("""
            INSERT INTO redirects (from_title, to_title)
            VALUES(%s, %s)
            ON CONFLICT DO NOTHING
          """, (from_title, to_title))

          conn.commit()

      element.clear()


def process_pages(wiki_file_path, conn, cursor):
  with bz2.open(wiki_file_path, mode='rb') as dump_file:
    context = etree.iterparse(dump_file, events=("end",), tag="{" + namespace_uri + "}page")

    for event, element in context:
      if event == "end":
        namespace = element.findtext("mw:ns", namespaces=ns_map)
        if namespace != "0":
          continue

        redirect_element = element.find("mw:redirect", namespaces=ns_map)
        if redirect_element is not None:
          continue

        title = element.findtext("mw:title", namespaces=ns_map)
        page_id = element.findtext("mw:id", namespaces=ns_map)
        content = element.findtext("mw:revision/mw:text", namespaces=ns_map)

        cleaned_content = clean_markup(content, keep_links=False, ignore_headers=True)
        content = str(list(cleaned_content))

        cursor.execute("""
          INSERT INTO nodes (id, grp, active)
          VALUES(%s, %s, %s)
        """, (page_id, 'NULL', True))

        cursor.execute("""
          INSERT INTO nodes_info (id, url, content)
          VALUES(%s, %s, %s)
        """, (page_id, page_title_to_link(title), content))

        conn.commit()

        element.clear()


def process_links(wiki_file_path, conn, cursor):
  with bz2.open(wiki_file_path, mode='rb') as dump_file:
    context = etree.iterparse(dump_file, events=("end",), tag="{" + namespace_uri + "}page")

    for event, element in context:
      if event == "end":
        namespace = element.findtext("mw:ns", namespaces=ns_map)
        if namespace != "0":
          continue

        redirect_element = element.find("mw:redirect", namespaces=ns_map)
        if redirect_element is not None:
          continue

        page_id = element.findtext("mw:id", namespaces=ns_map)
        content = element.findtext("mw:revision/mw:text", namespaces=ns_map)
        links = find_links(content)

        for link in links:
          link_dest = page_title_to_link(link)

          # let's check if they exist in redirects
          cursor.execute(
              "SELECT to_title FROM redirects WHERE from_title = %s LIMIT 1", (link_dest,))
          node_exists = cursor.fetchone()
          if node_exists is not None:
            link_dest = node_exists[0]

          # translating url to id
          cursor.execute("SELECT id FROM nodes_info WHERE url = %s LIMIT 1", (link_dest,))
          to_node_id = None
          node_exists = cursor.fetchone()
          if node_exists is None:
            # skipping link to not existing node
            continue
          else:
            to_node_id = node_exists[0]

          cursor.execute("""
            INSERT INTO edges (src, des, active)
            VALUES(%s, %s, TRUE)
            ON CONFLICT DO NOTHING
          """, (page_id, to_node_id))

        conn.commit()

        element.clear()


def load_multistream_dump(config, multistream_wiki_dump_folder_path):
  """
  Loads the wikipedia dump into the database. The multistream wikipedia dump is a series of bz2 files
  that contain the wikipedia pages in xml format. Each file contains a series of pages.
  """
  conn = psycopg2.connect(**config["database"])

  files = [os.path.join(multistream_wiki_dump_folder_path, f)
           for f in os.listdir(multistream_wiki_dump_folder_path)]

  # TODO REMOVE
  # files = list(filter(lambda fp: "multistream1.xml" in fp, files))

  # read redirects
  for f in files:
    cursor = conn.cursor()
    print("processing redirects for:", f)
    process_redirects(f, conn, cursor)
    cursor.close()

  # reading only nodes first
  for f in files:
    cursor = conn.cursor()
    print("processing nodes for:", f)
    process_pages(f, conn, cursor)
    cursor.close()

  # reading only edges (so we can remove ones that are not in the nodes)
  for f in files:
    cursor = conn.cursor()
    print("processing edges for:", f)
    process_links(f, conn, cursor)
    cursor.close()

  conn.close()


def load_multistream_dump_dry_run(config, multistream_wiki_dump_folder_path):
  files = [os.path.join(multistream_wiki_dump_folder_path, f)
           for f in os.listdir(multistream_wiki_dump_folder_path)]

  pages = 0
  for f in files:
    print("processing nodes for:", f)
    with bz2.open(f, mode='rb') as dump_file:
      context = etree.iterparse(dump_file, events=("end",), tag="{" + namespace_uri + "}page")

      for event, element in context:
        if event == "end":
          namespace = element.findtext("mw:ns", namespaces=ns_map)
          if namespace != "0":
            continue

          redirect_element = element.find("mw:redirect", namespaces=ns_map)
          if redirect_element is not None:
            continue

          pages += 1
          element.clear()
  print("Pages:", pages)


def vectorize_content(config):
  """
  vectorize the content and create an index to it
  """
  conn = psycopg2.connect(**config["database"])
  cursor = conn.cursor()
  try:
    cursor.execute("""
      UPDATE nodes_info
      SET content_vector = to_tsvector(
        'english',
        regexp_replace(regexp_replace(content, '[^[:alnum:]]', ' ', 'g'),
        '\\s+',
        ' ',
        'g'
      ));
      """)

    conn.commit()

    cursor.execute("""
        CREATE INDEX nodes_info_content_vector_idx
        ON nodes_info USING gin(content_vector);
      """)

    conn.commit()

  except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
  finally:
    cursor.close()
    conn.close()

  print("SQL operations completed.")


if __name__ == '__main__':
  import sys

  # get the path to the dump file from the command line
  if len(sys.argv) != 3:
    print("Usage: python3 load_wiki_dump.py <path to config.json> <path to dump file>")
    exit(1)
  config_json_path = sys.argv[1]
  config = None
  with open(config_json_path) as config_file:
    config = json.load(config_file)
  config["database"]["database"] = "newwikidump"

  dump_file_files_folder = sys.argv[2]

  load_multistream_dump(config, dump_file_files_folder)
  vectorize_content(config)
