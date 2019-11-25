DROP TABLE if EXISTS wn18_entity;
DROP TABLE if EXISTS wn18_relation;

CREATE TABLE wn18_entity(
   synset_id text PRIMARY KEY NOT NULL,
   doc text,
   POS_tag text,
   sense_index integer,
   definition text
);

CREATE TABLE wn18_relation(
   relation_id SERIAL PRIMARY KEY,
   doc text
);
