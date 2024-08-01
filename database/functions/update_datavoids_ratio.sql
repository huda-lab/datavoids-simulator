
-- To update the ratio value without going to compute the whole thing again
-- update datavoids set ratio = 
-- case 
--   when power(freq_ungrouped, 4) * (power(10, 2) * abs(freq_group_a - freq_group_b)) != 0 
--     then (
--       freq_group_a * freq_group_b) / (power(freq_ungrouped, 4) * 
--         (power(10, 4) * abs(freq_group_a - freq_group_b))
--     ) 
--   else 
--     null
-- end;

create or replace function update_datavoids_ratio(
  ratio_k float default 5, -- adjusts the penalty of freq_A(w) be different than freq_B(w).
  ratio_t float default 2  -- adjusts the influence of the ungrouped frequency
) returns void as $$
declare
begin

  update datavoids 
  set ratio = case 
    when power(freq_ungrouped, ratio_t) * 
      (power(10, ratio_k) * abs(freq_group_a - freq_group_b)) != 0 
    then (
        freq_group_a * freq_group_b) / 
      (power(freq_ungrouped, ratio_t) * 
      (power(10, ratio_k) * abs(freq_group_a - freq_group_b))
    )
    else 
      null
  end;

end;
$$ language plpgsql;
