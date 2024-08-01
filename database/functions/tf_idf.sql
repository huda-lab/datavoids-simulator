create or replace procedure calculate_tf_idf() as $$
declare
    word_record text;
    doc_record int;
    total_documents int;
    total_words_in_doc int;
    word_count int;
    documents_with_word int;
    tf numeric;
    idf numeric;
begin
    truncate word_tf_idf;
    select count(*) into total_documents from nodes_info;
    for doc_record in select id from nodes_info
    loop
        for word_record in select distinct grams from grams((select content from nodes_info where id=doc_record))
        loop
            select count(*) into total_words_in_doc from grams((select content from nodes_info where id=doc_record));
            select count(*) into word_count from grams((select content from nodes_info where id=doc_record)) where grams=word_record;
            tf := word_count::numeric / total_words_in_doc::numeric;
            select count(*) into documents_with_word from nodes_info where content ~* word_record;
            idf := log(total_documents::numeric / (1 + documents_with_word::numeric));
            insert into word_tf_idf (word, node_id, tf, idf, tf_idf) values (word_record, doc_record, tf, idf, tf*idf);
        end loop;
    end loop;
end;
$$ language plpgsql;

create or replace function update_important_terms(node_ids int[])
returns integer
language plpgsql
as $$
declare
    row_count integer;
begin

    drop table if exists important_terms;

    create table important_terms as
    with term_stats as (
        select 
            filtered_nodes.id as node_id, 
            nodes_words.word as word, 
            count(nodes_words.word)::integer as tf
        from (
            select id, unnest(tsvector_to_array(content_vector)) as word
            from nodes_info
            where id = any(node_ids)
        ) as nodes_words
        join (
            select id, content_vector
            from nodes_info
            where id = any(node_ids)
        ) as filtered_nodes
        on nodes_words.id = filtered_nodes.id
        group by filtered_nodes.id, nodes_words.word
    )
    select ts.word, ts.node_id, ts.tf
    from term_stats ts; 
 
    select count(*) into row_count from important_terms;

    return row_count;

end;
$$;

create or replace function compute_idf() returns void language plpgsql as $$
declare
    total_docs integer;
    word_record record;
    docs_with_word integer;
begin
    -- create only if doesn't exist
    if not exists (select 1 from pg_tables where tablename = 'idf_values') then
        create table idf_values (
            word text primary key,
            idf_value double precision
        );
    end if;
    truncate table idf_values;

    select count(*) into total_docs from nodes_info;

    -- iterate over each word from the content_vector of specified pages
    for word_record in
        select distinct unnest(tsvector_to_array(content_vector)) as word
        from nodes_info
    loop
        -- for each word, get the number of documents in the entire dataset that contain the word
        select count(*) into docs_with_word
        from nodes_info
        where content_vector @@ to_tsquery(word_record.word);

        -- compute the idf value for the word using the whole dataset and insert into the idf table
        insert into idf_values (word, idf_value) 
        values (
            word_record.word, 
            ln(total_docs::double precision / greatest(docs_with_word::double precision, 1)) -- using greatest() to prevent division by zero
        );
    end loop;
end;
$$;

-- like compute_idf, but for specific nodes, since doing for all is unfeasible
create or replace function compute_idf_seeds_nodes(p_ids integer[]) returns void language plpgsql as $$
declare
    total_docs integer;
    word_record record;
    docs_with_word integer;
    rec record;
begin
    if not exists (select 1 from pg_tables where tablename = 'idf_values_seeds_nodes') then
        create table idf_values_seeds_nodes (
            word text primary key,
            idf_value double precision
        );
    end if;
    truncate table idf_values_seeds_nodes;

    select count(*) into total_docs from nodes_info;

    -- iterate over each word from the content_vector of specified nodes
    for word_record in
        select distinct unnest(tsvector_to_array(content_vector)) as word
        from nodes_info
        where id = any(p_ids)
    loop
        -- for each word, get the number of documents in the entire dataset that contain the word
        select count(*) into docs_with_word
        from nodes_info
        where content_vector @@ to_tsquery(word_record.word);

        -- compute the idf value for the word using the whole dataset and insert into the idf table
        insert into idf_values_seeds_nodes (word, idf_value) 
        values (
            word_record.word, 
            ln(
                total_docs::double precision / greatest(docs_with_word::double precision, 1)
            ) -- using greatest() to prevent division by zero
        );
    end loop;
end;
$$;

create or replace function ungroup_nodes_with_no_topk_words(p_ids integer[], groups text[], k int)
returns void
language plpgsql
as $$
declare
    rec RECORD;
    top_k_words text[];
begin

    drop table if exists tfidf_values_seeds_nodes;
    create table tfidf_values_seeds_nodes (
        word text not null unique,
        word_count int,
        tf double precision,
        idf double precision,
        tfidf_score double precision
    );

    -- First, use the grams function to tokenize the content
    with words_per_document as (
        select 
            id,
            g.grams as word
        from nodes_info 
        cross join lateral grams_with_repetitions(content) g
        where id = any(p_ids)
    ),

    -- Then, create a histogram of word occurrences per document
    words_histogram as (
        select 
            id,
            word,
            count(word) as word_count
        from words_per_document
        group by id, word
    ),

    -- Compute the TF
    tf_per_document as (
        select 
            id,
            word,
            word_count,
            word_count::double precision / (select count(word) from words_per_document where id = wh.id)::double precision as tf
        from words_histogram wh
    ),

    -- Aggregate TF across all documents
    aggregate_tf as (
        select 
            word,
            avg(tf) as aggregated_tf,
            sum(word_count) as aggregated_word_count
        from tf_per_document
        group by word
    )

    -- Join with idf_values_seeds_nodes to get the idf and calculate tf-idf
    insert into tfidf_values_seeds_nodes(word, word_count, tf, idf, tfidf_score)
    select 
        w.word, 
        w.aggregated_word_count as word_count,
        w.aggregated_tf as tf,
        i.idf_value as idf,
        (w.aggregated_tf * i.idf_value) as tfidf_score
    from aggregate_tf w
    join idf_values_seeds_nodes i on w.word = i.word
    on conflict(word) do update 
    set tf = excluded.tf, idf = excluded.idf, tfidf_score = excluded.tfidf_score;

    select array_agg(word) into top_k_words from (
        select word from tfidf_values_seeds_nodes
        order by tfidf_score desc
        limit k
    ) as sub;

    -- drop table if exists topk_ifidf_words;
    -- create table topk_ifidf_words as (
    --     select * from tfidf_values_seeds_nodes
    --     order by tfidf_score desc
    -- );

      -- Transform the array of top k words into a tsquery where any of the words can match
    with tsquery_data as (
        select string_agg(plainto_tsquery(word)::text, '|') as tsquery_string
        from unnest(top_k_words) as word
    )
    -- Ungroup nodes without any of the top K words
    update nodes n
    set grp = null
    from nodes_info ni, tsquery_data
    where 
        n.id = ni.id
        and grp is not null
        and not (ni.content_vector @@ to_tsquery(tsquery_data.tsquery_string));

end;
$$;
