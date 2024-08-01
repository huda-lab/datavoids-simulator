-- 
-- Calling set_group_from_target_page(target_page_id, grp_name, N);
-- will set the grp_name of all nodes that are reachable from target_page_id
-- within N steps to the value of grp_name.
--
create or replace function set_group_from_target_page(
  target_page_id int,
  grp_name varchar,
  n_hops int
) returns void as $$
declare
begin
  raise notice 'set_group_from_target_page started';
  raise notice 'target_page_id: %', target_page_id;
  raise notice 'grp_name: %', grp_name;
  raise notice 'n_hops: %', n_hops;

  with recursive traversal(src, des, depth) as (
    select e.src, e.des, 1
    from edges e
    where e.des = target_page_id 

    union all

    select e.src, e.des, t.depth + 1
    from edges e
    join traversal t on e.des = t.src
    where t.depth < n_hops 
  ) 
  update nodes n
  set grp = concat_ws('|', n.grp, grp_name)
  where n.id in (
    select distinct src
    from traversal
  ) or n.id = target_page_id;
end;
$$ language plpgsql;
