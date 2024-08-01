-- I the case of groups with very different size, this function can be used to make them similar
create or replace function equalize_groups() returns void as $$
declare 
  higher_number_group varchar;
  group_record record;
  group_count int;
begin
  raise notice 'equalize_groups';

-- Determine the larger group
select grp into higher_number_group from (
  select grp, count(*) as count 
  from nodes 
  where grp is not null 
  group by grp 
  order by count desc 
  limit 1
) hng;

raise notice 'removing randomly the nodes from the higher group %', higher_number_group;

-- Delete approximately 50% of the nodes from the largest group randomly
update nodes set grp = null where grp = higher_number_group and random() < 0.5;

-- loop through all groups
for group_record in (select grp from nodes group by grp)
loop
    select into group_count count(*) from nodes where grp = group_record.grp and active = true;
    raise notice 'after deletion, group % has % nodes.', group_record.grp, group_count;
end loop;

end;
$$ language plpgsql;