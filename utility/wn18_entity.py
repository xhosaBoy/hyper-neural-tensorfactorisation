# std
import os
import sys
import re
import copy
import logging

# 3rd party
import psycopg2
from psycopg2.extras import Json
from psycopg2.extensions import AsIs


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def get_path(dirname, filename):
    """File path getter.
        Args:
            dirname (str): File directory.
            filename (str): File name.
        Returns:
            filepath (str): Full file file path.
        """
    util_dirname, _ =  os.path.split(__file__)
    project, _ = os.path.split(util_dirname)
    return os.path.join(project, dirname, filename)


def get_connection(user, password, host, port, database):
    """Database connection getter.
        Args:
            user (str): database user.
            password (str): database user password.
            host (str): database IP.
            port (str): database port.
            database (str): database name.
        Returns:
            connection (obj): postgres database connection.
        """
    connection = psycopg2.connect(user=user,
                                  password=password,
                                  host=host,
                                  port=port,
                                  database=database)
    return connection


def insert_record(record, tablename, connection):

    columns = record.keys()
    logger.debug(f'columns: {columns}')
    values = record.values()
    logger.debug(f'values: {values}')
    values = list(map(lambda x: Json(x) if isinstance(x, dict) else x, values))

    cursor = connection.cursor()
    relation = tablename
    attributes = AsIs(','.join(columns))
    values = tuple(values)
    insert_statement = f"""INSERT INTO {relation} ({attributes}) 
                           VALUES {values}
                        """
    logger.debug(f"cursor.mogrify: {cursor.mogrify(insert_statement)}")

    try:
        cursor.execute(insert_statement)
    except Exception as e:
        logger.error(f'Could not insert into {tablename}, {e}')

    connection.commit()
    count = cursor.rowcount
    logger.debug(f'{count} Record inserted successfully into {tablename} table')


def insert_records(records):
    with get_connection('scientist',
                        '*************',
                        '127.0.0.1',
                        '5432',
                        'tensor_factorisation') as connection:

        tablename = 'wn18_entity'

        for record in records:
            insert_record(record, tablename, connection)


def get_records(entityfile):
    with open(entityfile, 'r') as entityfile:
        records = []
        record = {}

        for line in entityfile:
            synset_id, intelligible_name, definition = line.strip().split('\t')
            logger.debug(f'synset_id: {synset_id}, intelligible_name: {intelligible_name}, defintion: {definition}')

            pattern = re.compile(r'^__([a-zA-Z0-9\'\._/-]*)_([A-Z]{2})_([0-9])')
            doc = pattern.search(intelligible_name).group(1).replace('_', ' ').replace('"', '\"').replace("'", '"')
            logger.debug(f'doc: {doc}')
            POS_tag = pattern.search(intelligible_name).group(2)
            logger.debug(f'POS_tag: {POS_tag}')
            sense_index = pattern.search(intelligible_name).group(3)
            logger.debug(f'sense_index: {sense_index}')

            definition = definition.replace('_', ' ').replace('"', '\"').replace("'", '"')

            record['synset_id'] = synset_id
            record['doc'] = doc
            record['POS_tag'] = POS_tag
            record['sense_index'] = int(sense_index)
            record['definition'] = definition

            logger.debug(f'record: {record}')
            records.append(copy.copy(record))

        logger.info(f'number of records: {len(records)}')

    return records


def main():
    entityfile = get_path('data/WN18', 'wordnet-mlj12-definitions.txt')
    logger.debug(f'entityfile: {entityfile}')
    records = get_records(entityfile)
    insert_records(records)


if __name__ == '__main__':
    main()