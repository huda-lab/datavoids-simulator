# Datavoids Web Simulator

This web simulator explores the dynamics of data voids and the effectiveness of different mitigation strategies. A data void occurs when there is a lack of relevant information online for certain search keywords, which can be exploited to spread disinformation. The entire English Wikipedia is used as dataset to simulate a web of hyperlinked Web pages.

Our simulator models an adversarial game between disinformers and mitigators, each attempting to influence search engine rankings by adding content to fill these voids:

- Simulation of Data Voids: the simulator constructs data voids by removing relevant pages from the Wikipedia dataset, creating an environment where search queries return few or no relevant results, mimicking real-world scenarios where data voids can be exploited.

- Adversarial Game Model: disinformers and mitigators take turns adding content to the dataset. Disinformers aim to promote misleading information, while mitigators attempt to counteract this by adding accurate information.

- Evaluation of Strategies: the simulator evaluates various strategies for both disinformers and mitigators. Strategies include Random, Greedy, and Multiobjective approaches, each with different resource allocations and impact levels.

- Tracking and Analysis: the simulator tracks the changes in search result rankings over time, providing insights into the effectiveness of different mitigation efforts.

Some of the results can be illustrated from our main research paper. The following figure shows the difference in effects between the mitigator and disinformer at every turn of the web search simulation across four data void scenarios:

![figure3](https://github.com/user-attachments/assets/16aafae9-fd1b-4e29-89f1-993f1fdbd78b)

This figure illustrates the costs associated with different mitigator strategies at each turn of the web search simulation across the same four data void scenarios as the previous figure.

![figure4](https://github.com/user-attachments/assets/fb017999-d14e-40bc-90df-3fee471410f0)


## Running the simulator 

### Python environment

```bash
pipenv install
pipenv shell
pipenv --venv # To know where is the virtual environment path
```

Specify that environment path as path in anytime a Jupyter Notebook in VSCode need to be run.

### Project configuration

The project is configured by a file `config.json`. This file is not included in this repository, but a template of this file is available as  `config.template.json`.

An example here:

```json
{
  "database": {
    "host": "localhost",
    "user": "postgres",
    "password": "postgres",
    "database": "wikidump"
  },
  "stored_functions_dir": "./database/functions/",
  "target_groups": [
    "mit",
    "dis",
    "None"
  ],
  "groups_colors": {
    "mit": "#16a085",
    "dis": "#f39c12",
    "None": "#000000"
  },
  "mitigator_keyword": "mit",
  "disinformer_keyword": "dis",
  "mit_keywords": [],
  "dis_keywords": [],
  "target_node": {
    "bay": 404412,
    "fre": 15537745
  },
  "page_rank_at_each_step": false,
  "compute_initial_rage_rank": false,
  "top_k": 1000,
  "steps_config": {
    "max_steps": -1,
    "max_atomic_steps": -1,
    "on_each_node": true,
    "on_each_edge": false
  },
  "costs": {
    "budget": -1 
  },
  "labeling_hops": 1,
  "datavoids": [],
  "output_filename": null,
  "gzip": true
}
```

### Create the database

Install Postgres and create a database to contain the whole Wikipedia dataset.

```sql
create database wikidump;
```

After connecting to the database create the necessary tables:

```sql
drop table if exists nodes, nodes_info, edges, redirects, rank;

create table nodes(
  id serial primary key, 
  grp varchar,
  active boolean default true
);

create table nodes_info (
    id integer primary key,
    url character varying,
    content text,
    content_vector tsvector,
    date_added timestamp without time zone
);
create index index_name on nodes_info (url);

create table edges(
  src int references nodes,
  des int references nodes,
  active boolean default true,
  primary key (src, des)
);

create table rank(
  id int primary key
  -- rank algorithm can add columns to it
);

create table info(
  id varchar primary key,
  prop varchar
);

create table redirects(
  from_title varchar primary key, 
  to_title varchar
);
```

Data can then be imported through the official Wikipedia dump files with:

```bash
PYTHONPATH=.:loaders/wikiextractor python loaders/load_wiki_dump.py config.json  ~/path/to/enwiki-multistream 
```

alternatively, an existing DB dump is already available of an already imported Wikipedia dump.

```bash
psql -U postgres -d wikidump -f ~/path/to/wikidump.sql
```

### Load stopwords

Execute the following:

```bash
pipenv run python ./loaders/load_stopwords.py
```

The stopwords are contained in `data/stopwords` and are coming from these databases:

file                                                          |  size  |  source                                                                                                                                                         |  description
--------------------------------------------------------------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
[CoreNLP (Hardcoded)](en/corenlp_hardcoded.txt)               |  28    |  [ ⇱ ](https://github.com/stanfordnlp/CoreNLP/blob/master/src/edu/stanford/nlp/coref/data/WordLists.java)                                                       |  Hardcoded in src/edu/stanford/nlp/coref/data/WordLists.java and the same in src/edu/stanford/nlp/dcoref/Dictionaries.java
[Ranks NL (Google)](en/ranksnl_oldgoogle.txt)                 |  32    |  [ ⇱ ](http://www.ranks.nl/stopwords)                                                                                                                           |  The short stopwords list below is based on what we believed to be Google stopwords a decade ago, based on words that were ignored if you would search for them in combination with another word. (ie. as in the phrase "a keyword").
[Lucene, Solr, Elastisearch](en/lucene_elastisearch.txt)      |  33    |  [ ⇱ ](https://github.com/apache/lucene-solr/blob/master/lucene/analysis/common/src/java/org/apache/lucene/analysis/en/EnglishAnalyzer.java)                    |  (NOTE: Some config files have extra 's' and 't' as stopwords.) An unmodifiable set containing some common English words that are not usually useful for searching.
[MySQL (InnoDB)](en/mysql_innodb.txt)                         |  36    |  [ ⇱ ](http://dev.mysql.com/doc/refman/8.0/en/innodb-ft-default-stopword-table.html)                                                                            |  A word that is used by default as a stopword for FULLTEXT indexes on InnoDB tables. Not used if you override the default stopword processing with either the innodb_ft_server_stopword_table or the innodb_ft_user_stopword_table option.
[Ovid (Medical information services)](en/ovid.txt)            |  39    |  [ ⇱ ](http://resourcecenter.ovid.com/site/products/fieldguide/umda/Stopwords.jsp)                                                                              |  Words of little intrinsic meaning that occur too frequently to be useful in searching text are known as "stopwords." You cannot search for the following stopwords by themselves, but you can include them within phrases.
[Bow (libbow, rainbow, arrow, crossbow)](en/bow_short.txt)    |  48    |  [ ⇱ ](http://www.cs.cmu.edu/~mccallum/bow/src/bow-20020213.tar.gz)                                                                                             |  Bow: A Toolkit for Statistical Language Modeling, Text Retrieval, Classification and Clustering. Short list hardcoded. Also includes 524 SMART derived list, same as MALLET. See http://www.cs.cmu.edu/~mccallum/bow/rainbow/
[LingPipe](en/lingpipe.txt)                                   |  76    |  [ ⇱ ](http://alias-i.com/lingpipe/docs/api/com/aliasi/tokenizer/EnglishStopTokenizerFactory.html)                                                              |  An EnglishStopTokenizerFactory applies an English stop list to a contained base tokenizer factory
[Vowpal Wabbit (doc2lda)](en/vw_lda.txt)                      |  83    |  [ ⇱ ](https://github.com/JohnLangford/vowpal_wabbit/blob/master/utl/vw-doc2lda)                                                                                |  Stopwords used in LDA example
[Text Analytics 101](en/t101_minimal.txt)                     |  85    |  [ ⇱ ](https://bitbucket.org/kganes2/text-mining-resources/downloads/minimal-stop.txt)                                                                          |  Minimal list compiled by Kavita Ganesan consisting of determiners, coordinating conjunctions and prepositions http://text-analytics101.rxnlp.com/2014/10/all-about-stop-words-for-text-mining.html
[LexisNexis®](en/lexisnexis.txt)                              |  100   |  [ ⇱ ](http://help.lexisnexis.com/tabula-rasa/totalpatent/noisewords_ref-reference?lbu=US&locale=en_US&audience=online)                                         |  “The following are 'noise words' and are never searchable: EVER HARDLY HENCE INTO NOR WERE VIZ. Others are 'noisy keywords' and are searchable by enclosing them in quotes.”
[Okapi (gsl.cacm)](en/okapi_cacm.txt)                         |  108   |  [ ⇱ ](http://www.staff.city.ac.uk/~andym/OKAPI-PACK/appendix-d.html)                                                                                           |  Cacm specific stoplist from Okapi
[TextFixer](en/texfixer.txt)                                  |  119   |  [ ⇱ ](http://www.textfixer.com/resources/common-english-words.txt)                                                                                             |  From textfixer.com Linked from Wiki page on Stop words.
[DKPro](en/dkpro.txt)                                         |  127   |  [ ⇱ ](https://github.com/dkpro/dkpro-toolbox/tree/master/dkpro.toolbox.corpus-asl/src/main/resources/corpus/stopwords)                                         |  Postgresql (Snowball derived)
[Postgres](en/postgresql.txt)                                 |  127   |  [ ⇱ ](https://www.postgresql.org/docs/9.1/static/textsearch-dictionaries.html#TEXTSEARCH-STOPWORDS)                                                            |  “Stop words are words that are very common, appear in almost every document, and have no discrimination value.”
[PubMed Help](en/pubmed.txt)                                  |  133   |  [ ⇱ ](https://www.ncbi.nlm.nih.gov/books/NBK3827/table/pubmedhelp.T.stopwords/)                                                                                |  Listed in PubMed Help pages.
[CoreNLP (Acronym)](en/corenlp_acronym.txt)                   |  150   |  [ ⇱ ](https://github.com/stanfordnlp/CoreNLP/blob/master/src/edu/stanford/nlp/util/AcronymMatcher.java)                                                        |  A set of words that should be considered stopwords for the acronym matcher
[NLTK](en/nltk.txt)                                           |  153   |  [ ⇱ ](http://www.nltk.org/book/ch02.html)                                                                                                                      |  According to [email](https://groups.google.com/forum/#!topic/nltk-users/YVF0S0Q_8k4) Van Rij. Sbergen (1979) "Information retrieval" (Butterworths, London). It's slightly expanded from [postgres](http://anoncvs.postgresql.org/cvsweb.cgi/pgsql/src/backend/snowball/stopwords/english.stop) postgresql.txt which was borrowed from snowball presumably.
[Spark ML lib](en/spark_mllib.txt)                            |  153   |  [ ⇱ ](https://github.com/apache/spark/blob/master/mllib/src/main/resources/org/apache/spark/ml/feature/stopwords/english.txt)                                  |  (Note: Same as NLTK) They were obtained from [postgres](http://anoncvs.postgresql.org/cvsweb.cgi/pgsql/src/backend/snowball/stopwords/) The English list has been [augmented](https://github.com/nltk/nltk_data/issues/22)
[MongoDB](en/mongodb.txt)                                     |  174   |  [ ⇱ ](https://github.com/mongodb/mongo/blob/master/src/mongo/db/fts/stop_words_english.txt)                                                                    |  Commit says 'Changed stop words files to the snowball stop lists'
[Quanteda](en/quanteda.txt)                                   |  174   |  [ ⇱ ](https://github.com/kbenoit/quantedaData/blob/master/stopwords/english.dat)                                                                               |  Has SMART and Snowball Default Lists. [Source](https://github.com/kbenoit/quantedaData/blob/master/stopwords/makestopwords.R)
[Ranks NL (Default)](en/ranksnl_default.txt)                  |  174   |  [ ⇱ ](http://www.ranks.nl/stopwords)                                                                                                                           |  (Note: Same as Default Snowball Stoplist, but RanksNL frequently cited as source) “This list is used in [Ranks NL] Page Analyzer and Article Analyzer for English text, when you let it use the default stopwords list.”
[Snowball (Original)](en/snowball_original.txt)               |  174   |  [ ⇱ ](https://github.com/snowballstem/snowball-website/blob/master/algorithms/english/stop.txt)                                                                |  Default Snowball Stoplist.
[Xapian](en/xapian.txt)                                       |  174   |  [ ⇱ ](https://github.com/xapian/xapian/blob/master/xapian-core/languages/stopwords/english.txt)                                                                |  (Note: uses Snowball Stopwords) “It has been traditional in setting up IR systems to discard the very commonest words of a language - the stopwords - during indexing.”
[R `tm`](en/r_tm.txt)                                         |  174   |  [ ⇱ ](https://r-forge.r-project.org/scm/viewvc.php/pkg/inst/stopwords/english.dat?view=markup&root=tm)                                                         |  R `tm` package uses snowball list and also has SMART.
[99webTools](en/99webTools)                                   |  183   |  [ ⇱ ](http://99webtools.com/blog/list-of-english-stop-words/)                                                                                                  |  “Stop Words are words which do not contain important significance to be used in Search Queries. Most search engine filters these words from search query before performing search, this improves performance.”
[Deeplearning4J](en/deeplearning4j.txt)                       |  194   |  [ ⇱ ](https://github.com/eclipse/deeplearning4j/blob/master/datavec/datavec-data/datavec-data-nlp/src/main/resources/stopwords)                                |  DL4J Stopwords are in 2 places - [stopwords](https://github.com/eclipse/deeplearning4j/blob/master/datavec/datavec-data/datavec-data-nlp/src/main/resources/stopwords) and [stopwords.txt](https://github.com/eclipse/deeplearning4j/blob/master/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp/src/main/resources/stopwords.txt). Probably derived from snowball. Some unusual entires eg: `----s`.
[Reuters Web of Science™](en/reuters_wos.txt)                 |  211   |  [ ⇱ ](https://images.webofknowledge.com/WOK46/help/WOS/ht_stopwd.html)                                                                                         |  “Stopwords are common, frequently used words such as articles (a, an, the), prepositions (of, in, for, through), and pronouns (it, their, his) that cannot be searched as individual words in the Topic and Title fields. If you include a stopword in a phrase, the stopword is interpreted as a word placeholder.”
[Function Words (Cook 1988)](en/cook1988_function_words.txt)  |  221   |  [ ⇱ ](http://www.viviancook.uk/Words/StructureWordsList.htm)                                                                                                   |  “This list of 225 items was compiled for practical purposes some time ago as data for a computer parser for student English. [Paper](http://www.viviancook.uk/Writings/Papers/CalicoPaper88.htm)
[Okapi (gsl.sample)](en/okapi_sample.txt)                     |  222   |  [ ⇱ ](http://www.staff.city.ac.uk/~andym/OKAPI-PACK/appendix-d.html)                                                                                           |  This Okapi is the BM25 Okapi. (Note: Included stopword text file is from all “F” “H” terms, as defined by defs.h) The GSL file contains terms that are to be dealt with in a special way by the indexing process. Each type is defined by a class code.
[Snowball (Expanded)](en/snowball_expanded.txt)               |  227   |  [ ⇱ ](https://github.com/snowballstem/snowball-website/blob/master/algorithms/english/stop.txt)                                                                |  NOTE: This Includes the extra words mentioned in [comments](http://snowball.tartarus.org/algorithms/english/stop.txt) “An English stop word list. Many of the forms below are quite rare (e.g. 'yourselves') but included for completeness.”
[DataScienceDojo](en/datasciencedojo.txt)                     |  250   |  [ ⇱ ](https://github.com/datasciencedojo/meetup/blob/master/real-time_sentiment/AzureML%20Code/Stop%20Words%20Simple%20List.csv)                               |  Used in a real-time sentiment AzureML demo for a meetup
[CoreNLP (stopwords.txt)](en/corenlp_stopwords.txt)           |  257   |  [ ⇱ ](https://github.com/stanfordnlp/CoreNLP/blob/master/data/edu/stanford/nlp/patterns/surface/stopwords.txt)                                                 |  Note: "a", "an", "the", "and", "or", "but", "nor" hardcoded in StopList.java also includes punctuation (!!, -lrb- …)
[OkapiFramework](en/okapiframework.txt)                       |  262   |  [ ⇱ ](https://bitbucket.org/okapiframework/okapi/src/master/okapi/steps/termextraction/src/main/resources/net/sf/okapi/steps/termextraction/stopWords_en.txt)  |  THIS IS NOT Okapi of BM25! (At least I don't think so) This list used in Okapi FRAMEWORK this Okapi is the Localization and Translation Okapi.
[Azure Gallery](en/azure.txt)                                 |  310   |  [ ⇱ ](https://gallery.azure.ai/Experiment/How-to-modify-default-stopword-list-1)                                                                               |  Slightly modified glasgow list.
[ATIRE (NCBI Medline)](en/atire_ncbi.txt)                     |  313   |  [ ⇱ ](http://www.atire.org/hg/atire/file/tip/source/stop_word.c)                                                                                               |  NCBI wrd_stop stop word list of 313 terms extracted from Medline. Its use is unrestricted. The list can be downloaded from [here](http://mbr.nlm.nih.gov/Download/2009/WordCounts/wrd_stop)
[Go](en/bbalet.txt)                                           |  317   |  [ ⇱ ](https://github.com/bbalet/stopwords/blob/master/stopwords_en.go)                                                                                         |  Go stopwords library. This is the glasgow list without 'computer' 'i' 'thick' - has 'thickv'
[scikit-learn](en/scikitlearn.txt)                            |  318   |  [ ⇱ ](https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/feature_extraction/stop_words.py)                                                       |  Uses Glasgow list, but without the word “computer”
[Glasgow IR](en/glasgow_stop_words.txt)                       |  319   |  [ ⇱ ](http://ir.dcs.gla.ac.uk/resources/linguistic_utils/stop_words)                                                                                           |  Linguistic resources from Glasgow Information Retrieval group. Lots of copies and edits of this one. Eg: [xpo6](http://xpo6.com/wp-content/uploads/2015/01/stop-word-list.txt) has mistakes – has quote instead of 'lf' eg: herse" instead of herself - comes up as one of the top results in google search.
[xpo6](en/xpo6.txt)                                           |  319   |  [ ⇱ ](http://xpo6.com/list-of-english-stop-words/)                                                                                                             |  Used in Humboldt Diglital Library and Network and documented in blogpost. Likely derived from Glasgow list.
[spaCy](en/spacy.txt)                                         |  326   |  [ ⇱ ](https://github.com/explosion/spaCy/blob/master/spacy/lang/en/stop_words.py)                                                                              |  Improved list from Stone, Denis, Kwantes (2010) [Paper](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.456.3709&rep=rep1&type=pdf)
[Gensim](en/gensim.txt)                                       |  337   |  [ ⇱ ](https://github.com/RaRe-Technologies/gensim/blob/master/gensim/parsing/preprocessing.py)                                                                 |  Same as spaCy (Improved list from Stone, Denis, Kwantes (2010))
[Okapi (Expanded gsl.cacm)](en/okapi_cacm_expanded.txt)       |  339   |  [ ⇱ ](http://www.staff.city.ac.uk/~andym/OKAPI-PACK/appendix-d.html)                                                                                           |  Expanded cacm list from Okapi
[C99 and TextTiling](en/choi_2000naacl.txt)                   |  371   |  [ ⇱ ](https://code.google.com/archive/p/uima-text-segmenter/source/default/source)                                                                             |  UIMA wrapper for the java implementations of the segmentation algorithms C99 and TextTiling, written by Freddy Choi
[Galago (inquery)](en/galago_inquery.txt)                     |  418   |  [ ⇱ ](https://sourceforge.net/p/lemur/galago/ci/default/tree/core/src/main/resources/stopwords/inquery)                                                        |  The core/src/main/resources/stopwords/inquery list is same as Indri default.
[Indri](en/indri.txt)                                         |  418   |  [ ⇱ ](https://sourceforge.net/p/lemur/code/HEAD/tree/indri/trunk/site-search/stopwords)                                                                        |  Part of Lemur Project
[Onix & Lextek](en/onix.txt)                                  |  429   |  [ ⇱ ](http://www.lextek.com/manuals/onix/stopwords1.html)                                                                                                      |  This stopword list is probably the most widely used stopword list. It covers a wide number of stopwords without getting too aggressive and including too many words which a user might search upon. This wordlist contains 429 words.
[GATE (Keyphrase Extraction)](en/gate_keyphrase.txt)          |  452   |  [ ⇱ ](https://gate.ac.uk/gate/plugins/Keyphrase_Extraction_Algorithm/src/kea/StopwordsEnglish.java)                                                            |  Stopwords used in GATE Keyphrase Extraction Algorithm
[Zettair](en/zettair.txt)                                     |  469   |  [ ⇱ ](http://www.seg.rmit.edu.au/zettair/download.html)                                                                                                        |  Zettair is a compact and fast text search engine designed and written by the Search Engine Group at RMIT University. It was once known as Lucy.
[Okapi (Expanded gsl.sample)](en/okapi_sample_expanded.txt)   |  474   |  [ ⇱ ](http://www.staff.city.ac.uk/~andym/OKAPI-PACK/appendix-d.html)                                                                                           |  Same as okapi_sample.txt but with “I” terms (not default Okapi behaviour! but may be useful)
[Taporware](en/taporware.txt)                                 |  485   |  [ ⇱ ](http://taporware.ualberta.ca/~taporware/cgi-bin/prototype/glasgowstoplist.txt)                                                                           |  TAPoRware Project, McMaster University - modified Glasgow list – includes numbers 0 to 100, and 1990 to 2020 (for dates presumably) also punctuation
[Voyant (Taporware)](en/voyant_taporware.txt)                 |  488   |  [ ⇱ ](https://github.com/sgsinclair/trombone/blob/master/src/main/resources/org/voyanttools/trombone/keywords/stop.en.taporware.txt)                           |  Voyant uses taporware list by default, includes extra thou, thee, thy – presumably for Shakespeare corpus. Trombone repo also has Glasgow and SMART in resources.
[MALLET](en/mallet.txt)                                       |  524   |  [ ⇱ ](https://github.com/mimno/Mallet/blob/master/src/cc/mallet/pipe/TokenSequenceRemoveStopwords.java)                                                        |  Default MALLET stopword list. (Based on SMART I think) See [Docs](http://mallet.cs.umass.edu/import-stoplist.php)
[Weka](en/weka.txt)                                           |  526   |  [ ⇱ ](https://svn.cms.waikato.ac.nz/svn/weka/trunk/weka/src/main/java/weka/core/stopwords/Rainbow.java)                                                        |  Like Bow (Rainbow, which is SMART) but with extra ll ve added to avoid words like you'll,I've etc. Almost exactly the same as mallet.txt
[MySQL (MyISAM)](en/mysql_myisam.txt)                         |  543   |  [ ⇱ ](https://dev.mysql.com/doc/refman/5.6/en/server-system-variables.html#sysvar_ft_stopword_file)                                                            |  MyISAM and InnoDB use different stoplists. Taken from SMART but [modified](http://lists.mysql.com/mysql/165037?f=plain)
[Galago (rmstop)](en/galago_rmstop.txt)                       |  565   |  [ ⇱ ](https://sourceforge.net/p/lemur/galago/ci/default/tree/core/src/main/resources/stopwords/rmstop)                                                         |  Includes some punctuation, utf8 characters, www, http, org, net, youtube, wikipedia
[Kevin Bougé](en/kevinbouge.txt)                              |  571   |  [ ⇱ ](https://sites.google.com/site/kevinbouge/stopwords-lists)                                                                                                |  Multilang lists compiled by Kevin Bougé. English is SMART.
[SMART](en/smart.txt)                                         |  571   |  [ ⇱ ](http://ftp.gnome.org/mirror/archive/ftp.sunet.se/pub/databases/full-text/smart/english.stop)                                                             |  SMART (System for the Mechanical Analysis and Retrieval of Text) Information Retrieval System is an information retrieval system developed at Cornell University in the 1960s.
[ROUGE](en/rouge_155.txt)                                     |  598   |  [ ⇱ ](https://github.com/andersjo/pyrouge/blob/master/tools/ROUGE-1.5.5/data/smart_common_words.txt)                                                           |  Extended SMART list used in ROUGE 1.5.5 Summary Evaluation Toolkit – includes extra words: reuters, ap, news, tech, index, 3 letter days of the week and months.
[tonybsk_1.txt](en/tonybsk_1.txt)                             |  635   |  [ ⇱ ](https://github.com/igorbrigadir/stopwords/blob/master/en/tonybsk_1.txt)                                                                                  |  Unknown origin - I lost the reference.
[Sphinx Search Ultimate](en/sphinx_mirasvit.txt)              |  665   |  [ ⇱ ](https://mirasvit.com/doc/extension_searchultimate/current/dictionaries/stopwords/en.txt)                                                                 |  An extension for Sphinx has this list.
[Ranks NL (Large)](en/ranksnl_large.txt)                      |  667   |  [ ⇱ ](http://www.ranks.nl/stopwords)                                                                                                                           |  A very long list from ranks.nl
[tonybsk_6.txt](en/tonybsk_6.txt)                             |  671   |  [ ⇱ ](https://github.com/igorbrigadir/stopwords/blob/master/en/tonybsk_6.txt)                                                                                  |  Unknown origin - I lost the reference.
[Terrier](en/terrier.txt)                                     |  733   |  [ ⇱ ](http://terrier.org/docs/v4.1/javadoc/org/terrier/terms/Stopwords.html)                                                                                   |  Terrier Retrieval Engine “Stopword list to load can be loaded from the stopwords.filename property.”
[ATIRE (Puurula)](en/atire_puurula.txt)                       |  988   |  [ ⇱ ](http://www.atire.org/hg/atire/file/tip/source/stop_word.c)                                                                                               |  Included in ATIRE See [Paper](http://www.aclweb.org/anthology/U13-1013)
[Alir3z4](en/alir3z4.txt)                                     |  1298  |  [ ⇱ ](https://github.com/Alir3z4/stop-words/blob/master/english.txt)                                                                                           |  List of common stop words in various languages. The English list looks like merged from several sources.

### TF-IDF

Compute TF-IDF following the notebook `tf_idf.ipynb`. The reason is not a straighforward python file to execute is to give enough configurability in this part. For example IDF is only computed on the topics you are interested about, but a command to calculate for all pages in wikipedia is commented out and available, but it might take several weeks to run on a laptop.

Remember in this notebook the stored procedure `compute_idf_seeds_nodes` will take a long time to execute. On a M1 Pro Macbook Pro it finished in 7 hours.

Alternatively a computed TF-IDF is stored in `wikidump_tf_idf.sql` and you can import with:

```bash
psql -U postgres -d wikidump -f ~/path/to/wikidump_tf_idf.sql
```

### Performances (optional)

#### Postgres

Increase shared_buffers to 1/4 of your RAM

```bash
sudo nvim /usr/local/var/postgres@14/postgresql.conf
```

Edit shared_buffers, for example for 16GB of ram calculated with PGTune.leopard.in.ua

```bash
max_connections = 40
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 500
random_page_cost = 1.1
work_mem = 26214kB
min_wal_size = 4GB
max_wal_size = 16GB
```

Restart postgres

```bash
brew services restart postgresql@14
```

#### Test with wikilite (optional)

In order to run faster simulation in development phase is possible to run in a smaller copy of the wikipedia pages network 
containing only nodes that are labeled, its neighgboors, and a random sample of the unlabeled ones.

In order to do this, first import wikipedia dump as well in another database.

```sql
create database wikilite;
```

Import dumps like the above steps done for `wikidump`.

Then everytime you run a simulation have `wikilite` as database instead of another database. This
database name is reserved for this kind of execution where tables like `nodes` is copied in a smaller
one to improve simulation performances.

### Important Folders and files

- *docs* folder contains some more details about the simulator with the description of strategies, how costs were modeled and various documents explaing the decision making behind.

- *database* folder contains SQL files which the code uses. For example, `functions/searchrank.sql` contains the algorithm for the search rank which performs pagerank and text search rank, which are respectively in `functions/pagerank.sql` and `functions/tsrank.sql`

- *data* folder contains various data needed for the simulator to work. Most importantly `data/datavoids_per_topic_filtered.json` contains the topics used for the paper, while `data/datavoids_per_topic.json` contains more topics that were considered and found to be not compelling.

- *hcp* folder contains files useful to run the simulator in the HPC

- *results* folder is where results are saved when simulations are running

- *tests* is where tests are. Important tests are:
  - `strategy-evaluation-all-topics.ipynb` which takes several days to finish, and runs all simulations for all topics. This produces files in the `results` folder. For example "pro_dec-eval-all-rnd-greedy.csv" is saved for the simuation of the topic Procedural Languages vs. Declarative Languages, running random vs greedy respectively. ('eval-all' indicates just a label in the simulation about the evaluation of all topics)
  - To plots the results of those run `strategy-evaluation-all-topics-results-single-plots.ipynb` and this will crate files in `results` folder, for example in `results/images_against_disinformer` images such as `opt-pes-eval-all-base-rnd-rnd-eval-all-greedy-rnd.pdf` are created.

- *PubVisualizations* also contains scripts and data to produce some paper visualizations.
