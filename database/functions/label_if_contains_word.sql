create or replace function contains_word_labeler(words_list text[], grp_name text) 
returns void as $$
begin
    with search_query as (
        select plainto_tsquery(word) as tsq
        from unnest(words_list) as word
    )
    update nodes
    set grp = grp_name
    from nodes_info, search_query
    where nodes.id = nodes_info.id and
          nodes_info.content_vector @@ search_query.tsq;
end;
$$ language plpgsql;
