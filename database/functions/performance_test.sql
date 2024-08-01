create or replace procedure performance_test()
language plpgsql
as $$
declare
    starttime timestamp;
    endtime timestamp;
begin
    starttime := clock_timestamp();
    -- something
    endtime := clock_timestamp();
    raise notice 'insert operations: % ms', extract(milliseconds from (endtime - starttime));
end;
$$;
