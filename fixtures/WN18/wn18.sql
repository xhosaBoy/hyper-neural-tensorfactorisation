DROP TABLE if EXISTS entity;
DROP TABLE if EXISTS relation;

CREATE TABLE entity(
   synset_id text PRIMARY KEY NOT NULL,
   doc text,
   POS_tag text,
   sense_index integer,
   definition text
);

CREATE TABLE relation(
   relation_id SERIAL PRIMARY KEY,
   doc text
);
