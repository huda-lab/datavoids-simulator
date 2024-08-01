
-- SET LOCAL tsvector_limit = '16MB';
UPDATE nodes_info 
SET content_vector = to_tsvector('english', regexp_replace(regexp_replace(content, '[^[:alnum:]]', ' ', 'g'), '\s+', ' ', 'g'));
create index nodes_info_content_vector_idx on nodes_info using gin(content_vector);

-- Querying now something like this will be fast
SELECT count(*) FROM nodes_info WHERE content_vector @@ to_tsquery('english', 'apple & banana');
