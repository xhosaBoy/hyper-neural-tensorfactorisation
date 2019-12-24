create view fact (id, subject, s_name, predicate, object, o_name) as
select S.id, S.subject, S.name, S.predicate, O.object, O.name
from (select train.id as id, subject, predicate, object, synset_id, name
from train join entity
on subject = synset_id) S, (select train.id as id, subject, predicate, object, synset_id, name
from train join entity
on object = synset_id) O
where S.id = O.id
