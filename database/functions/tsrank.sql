create or replace function tsrank(keyword text)
returns void as $$
declare
  ts_rank_min double precision;
  ts_rank_max double precision;
  l2_norm_tsrank double precision;
  start_time timestamp;
  end_time timestamp;
begin
  raise notice 'tsrank started';
  start_time := clock_timestamp();

  -- Add tsrank column if it doesn't exist
  alter table rank add column if not exists tsrank double precision;

  -- Calculate and store raw ts_rank values in tsrank column
  update rank
  set tsrank = ts_rank(nodes_info.content_vector, to_tsquery(keyword))
  from nodes_info
  where rank.id = nodes_info.id;

  -- Normalization with L^2
  l2_norm_tsrank = (select sqrt(sum(tsrank * tsrank)) from rank);
  raise notice 'l² norm for tsrank: %', l2_norm_tsrank;
  if l2_norm_tsrank != 0 then
      update rank set tsrank = tsrank / l2_norm_tsrank;
  else
      update rank set tsrank = 1;
  end if;

  -- Remap to [0,1]
  select min(tsrank), max(tsrank) into ts_rank_min, ts_rank_max from rank;
  update rank set tsrank = (tsrank - ts_rank_min) / (ts_rank_max - ts_rank_min);

  end_time := clock_timestamp();
  raise notice 'tsrank finished in: %', (end_time - start_time);
end;
$$ language plpgsql;
