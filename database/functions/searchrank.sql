create or replace function searchrank(keyword text)
returns void as $$
declare
  rank_min double precision;
  rank_max double precision;
  start_time timestamp;
  end_time timestamp;
begin
  raise notice 'searchrank started';
  start_time := clock_timestamp();

  -- execute this only if there are no rows in the table
  if not exists (select * from rank) then
    insert into rank(id) select id from nodes;
    perform pagerank();
  end if;

  perform tsrank(keyword);
  
  -- add columns if they don't exist
  alter table rank add column if not exists searchrank double precision;

  update rank set searchrank = (tsrank + pagerank) / 2;

  -- Remap to [0,1]
  select min(searchrank), max(searchrank) into rank_min, rank_max from rank;
  update rank set searchrank = (searchrank - rank_min) / (rank_max - rank_min);

  end_time := clock_timestamp();
  raise notice 'searchrank finished in: %', (end_time - start_time);
end;
$$ language plpgsql;