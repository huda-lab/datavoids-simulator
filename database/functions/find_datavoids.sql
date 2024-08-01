create or replace function find_datavoids(
    group_a varchar,
    group_b varchar,
    grouped_nodes_min_freq int default 0.1
) returns void as $$
declare
    group_a_nodes integer;
    group_b_nodes integer;
    ungrouped_nodes integer;
begin
    raise notice 'datavoids n-grams started';

-- Results are stored in datavoids
create table if not exists datavoids (
  gram text,
  freq_group_a float,
  freq_group_b float,
  freq_ungrouped float,
  ratio float
);

select count(*) into group_a_nodes from nodes nc where nc.grp like concat('%', group_a, '%');
select count(*) into group_b_nodes from nodes nc where nc.grp like concat('%', group_b, '%');
select count(*) into ungrouped_nodes from nodes nc where nc.grp is null;
 
with tmp_grp_a as (
  select gram,
    count(*)::float / group_a_nodes as freq
  from nodes_info ni
    natural join nodes n,
    grams(ni.content) t(gram)
  where n.grp like CONCAT('%', group_a, '%') 
  group by gram
),
tmp_grp_b as (
  select gram,
    count(*)::float / group_b_nodes as freq
  from nodes_info ni
    natural join nodes n,
    grams(ni.content) t(gram)
  where n.grp like CONCAT('%', group_b, '%') 
  group by gram
),
grams_groups as (
  select tmp_grp_a.gram gram,
    tmp_grp_a.freq freq_a,
    tmp_grp_b.freq freq_b
  from tmp_grp_a
    INNER JOIN tmp_grp_b ON tmp_grp_a.gram = tmp_grp_b.gram
  where tmp_grp_a.freq > grouped_nodes_min_freq
    and tmp_grp_b.freq > grouped_nodes_min_freq
),
grams_ungrouped as (
  select gram,
    count(*)::float / ungrouped_nodes as freq
  from nodes_info ni
    natural join nodes n,
    grams(ni.content) t(gram)
  where n.grp is null 
  group by gram
)
insert into datavoids (
    gram,
    freq_group_a,
    freq_group_b,
    freq_ungrouped,
    ratio
  )
select 
  grams_groups.gram,
  grams_groups.freq_a as freq_a,
  grams_groups.freq_b as freq_b,
  coalesce(grams_ungrouped.freq, 0) as freq_ungrouped,
  null as ratio
FROM grams_groups
  LEFT JOIN grams_ungrouped ON grams_groups.gram = grams_ungrouped.gram;
end;
$$ language plpgsql;
