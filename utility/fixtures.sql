DROP TABLE if EXISTS wn18_entity;

CREATE TABLE wn18_entity(
   synset_id text PRIMARY KEY NOT NULL,
   doc text,
   POS_tag text,
   sense_index integer,
   definition text
);