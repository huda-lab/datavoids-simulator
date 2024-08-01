create or replace function pagerank() returns void as 
$$
	declare 
		num_nodes integer;
		min_diff double precision := 1;
		min_precision_threshold double precision := 0.000001;
		damping_factor float := 0.85;
		teleporting_probability float := 1 - damping_factor;
		iterate boolean := true;
		iteration integer := 0;
		max_iteration integer := 2;
		start_time timestamp;
		end_time timestamp;
		min_pagerank double precision; 
		max_pagerank double precision;
		l2_norm double precision;
	begin
		raise notice 'pagerank started';
		start_time := clock_timestamp();

		if not exists (select * from rank) then
			insert into rank(id) select id from nodes;
		end if;

		-- get the total number of nodes in the edges table
		select count(*) into num_nodes from nodes where active = true;
		raise notice 'number of nodes: %', num_nodes; 

		alter table rank add column if not exists pagerank double precision;
		update rank
			set pagerank = 1.00 / num_nodes
			from nodes
			where rank.id = nodes.id;
		raise notice 'initial pagerank created with values all: %', 1.00 / num_nodes; 

		-- compute the weight of each edge
		create temp table edges_with_outer_degree as 
		with weight as (
			select src as id, 1.00 / count(des) as odeg from edges where active = true group by src
		)
		select edges.src as id, edges.des, weight.odeg 
		from edges join weight on edges.src = weight.id where edges.active = true;

		while iterate loop
			raise notice 'pagerank iteration: %', iteration;

			-- compute the pagerank score for each node
			create temp table new_pagerank as 
			with temp_pagerank as (
				select edges_with_outer_degree.des as id, 
								sum(rank.pagerank * edges_with_outer_degree.odeg * damping_factor) as pagerank 
				from rank 
				left join edges_with_outer_degree 
				on rank.id = edges_with_outer_degree.id
				group by edges_with_outer_degree.des
			) 
			select 
				rank.id, 
				teleporting_probability / num_nodes + coalesce(temp_pagerank.pagerank, 0) as pagerank 
			from rank 
			left join temp_pagerank 
			on rank.id = temp_pagerank.id;

			-- set min_diff to check for convergence
			select sqrt(sum((rank.pagerank - new_pagerank.pagerank)^2)) into min_diff 
			from rank 
			join new_pagerank 
			on rank.id = new_pagerank.id;
			
			if min_diff < min_precision_threshold then
				iterate := false;
			end if;

			-- replace the old pagerank table with the new one
			update rank
				set pagerank = new_pagerank.pagerank 
			from new_pagerank
			where rank.id = new_pagerank.id;
			drop table new_pagerank;

			iteration := iteration + 1;

			if iteration >= max_iteration then
				iterate := false;
			end if;

		end loop;

		drop table if exists edges_with_outer_degree;

		-- Normalization with L^2
		l2_norm = (select sqrt(sum(pagerank * pagerank)) from rank);
		if l2_norm != 0 then
				update rank set pagerank = pagerank / l2_norm;
		else
				update rank set pagerank = 1;
		end if;

		-- Remap to [0,1]
		min_pagerank = (select min(pagerank) from rank);
		max_pagerank = (select max(pagerank) from rank);
		if max_pagerank = min_pagerank then
			update rank set pagerank = 1;
		else
			update rank set pagerank = (pagerank - min_pagerank) / (max_pagerank - min_pagerank);
		end if;

		end_time := clock_timestamp();
		raise notice 'pagerank finished in: %', (end_time - start_time);
	end;
$$ language plpgsql;