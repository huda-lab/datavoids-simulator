-- To extract only words from a text, we need to remove HTML entities, non-alphanumeric characters, 
-- apostrophes, extra spaces and trim leading/trailing whitespace.
create or replace function only_words_in_text(txt text)
returns text as $$
begin
  txt := regexp_replace(txt, '\\s', '', 'g'); -- remove '\s' created by wikiextractor
  txt := regexp_replace(txt, '&[a-za-z0-9]+;', ' ', 'g'); -- remove HTML entities
  txt := regexp_replace(txt, 'https?://[^\s]*', '', 'g'); -- remove URLs
  txt := regexp_replace(txt, '[^a-zA-Z\s]', ' ', 'g'); -- remove anything that is not letters
  txt := regexp_replace(txt, '''+', '', 'g'); -- remove apostrophes
  txt := regexp_replace(txt, '\s+', ' ', 'g'); -- remove extra spaces and trim leading/trailing whitespace
  return trim(txt);
end;
$$ language plpgsql;

-- This function splits the input text into words and then aggregates n words together to form n-grams and
-- returns a table containing n-grams.
create or replace function grams(text_content text)
returns table(grams text) as $$
begin
  text_content := only_words_in_text(text_content);
  return query (
    with words as (
      select row_number() over () as rn, word
      from regexp_split_to_table(lower(text_content), E'\\s+|\\.|,|!|\\?') t(word)
    )
    select distinct word from words 
    where word is not null and word not in (select word from stopwords)
  );
end;
$$ language plpgsql;

-- This function splits the input text into words and then aggregates n words together to form n-grams and
-- returns a table containing n-grams.
create or replace function grams_with_repetitions(text_content text)
returns table(grams text) as $$
begin
  text_content := only_words_in_text(text_content);
  return query (
    with words as (
      select row_number() over () as rn, word
      from regexp_split_to_table(lower(text_content), E'\\s+|\\.|,|!|\\?') t(word)
    )
    select word from words 
    where word is not null and word not in (select word from stopwords)
  );
end;
$$ language plpgsql;