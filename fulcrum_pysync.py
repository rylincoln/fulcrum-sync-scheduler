# author = ry blaisdell - with a lot of stackoverflow articles
# this script integrates with a fulcrum app form that has records defining forms to sync to a "local"
# postgres database. it will add the table the first time, then using pangres upsert records afterwards
# after creating the tables it will then add a SERIAL UNIQUE objectid field to make arc products happier
# finally it will create a spatial view using postgis functions that can be added to arcmap and registered with the geodatabse
# registering with the geodatabase is not included in this script - because of dependency on arcpy/licensing
from fulcrum import Fulcrum
from sqlalchemy import create_engine, Column, Integer, String, inspect, Numeric, Time, Date, Sequence, ARRAY, DateTime
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import declarative_base
import pandas as pd
from dotenv import load_dotenv
import io
import os
from pangres import upsert
import re

# get os env
load_dotenv()

# set the fulcrum token
token = os.getenv('TOKEN')
fulcrum = Fulcrum(key=token)

# production postgresql db
engine = create_engine(os.getenv('DBSTRING'), echo=False, pool_size=10, max_overflow=20)

# get all the forms from the config app
forms = fulcrum.query('SELECT form_id,app_name, create_spatial_view FROM "08134861-d511-42ad-949d-ec4db2897434" WHERE _status = \'enabled\'')
# get all the form ids
form_ids = forms['rows']

# add an objectid if one doesn't exist (to make arcXXX happy) and create a spatial view of the table if one doesn't exist
def addObjectIDandCreateView(tablename):
    try:
        with engine.connect() as con:
            # add the objectid field (if there isn't one)
            oidStatement = text(f"""ALTER TABLE if exists {tablename} ADD IF NOT EXISTS objectid SERIAL UNIQUE""")
            con.execute(oidStatement)

            # does a view already exist?
            viewExistsStatement = text(f"""SELECT EXISTS (
                                            SELECT FROM information_schema.tables 
                                            WHERE  table_schema = 'arcgisuser'
                                            AND    table_name   = '{tablename}_view'
                                            );""")
            checkExists = con.execute(viewExistsStatement)

            exists = checkExists.fetchone()[0]

            # if no view exists, make one, with a shape column how arc likes it (i think)
            if exists == False:
                
                viewStatement = text(f"""CREATE OR REPLACE VIEW {tablename}_view AS (
                    SELECT
                    st_setsrid(st_point(_longitude, _latitude), 4326)::geometry(Point,4326) AS shape,
                    *
                    FROM {tablename}
                )""")

                con.execute(viewStatement)
    except Exception as error:
        print("hmm" + str(error))
        pass
    

# create the table from the fulcrum forms before passing it to the addObjectIDandCreateView() function
def createFlatTable(queryDF, tablename):
    try:
        print('hi ' + tablename)
        upsert(engine=engine,
                df=queryDF,
                table_name=tablename,
                if_row_exists='update',
                add_new_columns=True,
                schema='arcgisuser',
                )
        print('Seems like it works!')
        print('checking/adding oid field')

        addObjectIDandCreateView(tablename)

    except Exception as error:
        print("wahwah" + str(error))
        pass

# loop through the form IDs and call fulcrum for each - currently just a SELECT * FROM parentlevel.
# TODO add ability to define custom query in the config app
def callFulcrum(form_ids):
    try:
        # query object for each query we use to get our data from Fulcrum
        queries = {}
        # loop over the form ids
        for obj in form_ids:
            tableName = obj['app_name']

            # sanitize the table names
            tableNameClean = re.sub(r'[^a-zA-Z0-9 \n\.]', '_', tableName).lower().replace(' ','_')
            tableNameCleaner = re.sub('_+', '_', tableNameClean)
            # get the form data
            queries[tableNameCleaner] = 'SELECT * FROM "' + obj['form_id'] + '"'
        
        # call fulcrum and then send the result through the createTable and addObjectIDandCreateView functions
        for query in queries:
            data = fulcrum.query(queries[query], format='csv')
            # get the fields for this table
            fields = fulcrum.query(queries[query], format='json')['fields']

            # explicitly force soem dtypes in pandas - so this get's passed down to pangres -> postgresql
            dtypes = {}
            for field in fields:
                # skip these fields as we'll let parse_dates pandas functions handle them
                if field['name'] in ('_updated_at','_created_at','_server_updated_at','_server_created_at'):
                    pass
                elif field['type'] == 'integer':
                    dtypes.update({ field['name'] : 'Int64'})
                elif field['type'] == 'double':
                    dtypes.update({ field['name'] : 'float64'})
                else:
                    dtypes.update({ field['name'] : 'string'})
                                
            queryDF = pd.read_csv(io.StringIO(data.decode('utf-8')), index_col='_record_id', dtype=dtypes, parse_dates=['_updated_at','_created_at','_server_updated_at','_server_created_at'])
            createFlatTable(queryDF, query)
    except Exception as error:
        print('uh-oh ' + str(error))
        pass

# start the thing
callFulcrum(form_ids)
