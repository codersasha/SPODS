#!/usr/bin/python

# use SQLite for now
import sqlite3
import json

from UserDict import IterableUserDict

class Field(object):
    type_map = {
        str: ("TEXT", str),
        int: ("INTEGER", int),
        tuple: ("TEXT", json.dumps)
    }
    
    def __init__(self, title, python_type=None, null=None, default=None, pk=None):
        self.title = title
        self.python_type = python_type
        self.null = null
        self.default = default
        self.pk = pk

        self.sql_type = None
        self.type_converter = None
        if self.python_type != None:
            self.sql_type = self.type_map[self.python_type][0]
            self.type_converter = self.type_map[self.python_type][1]

class Table(object):
    def __init__(self, title, fields=[]):
        self.title = title
        self.fields = fields

    def create_table_stmt(self):
        query = "CREATE TABLE %s (" % self.title

        for field in self.fields:
            # 1. title
            query += " %s " % field.title

            # 1b. type
            if field.sql_type != None:
                query += " %s " % field.sql_type

            # 2. null or not null
            if field.null == False:
                query += " NOT NULL "

            # 3. default val
            if field.default != None:
                query += " DEFAULT %r " % (field.default)

            # 4. primary key?
            if field.pk == True:
                query += " PRIMARY KEY "

            # 5. comma
            query += " ,"

        # remove last comma
        query = query[:-1]
        query += ")"
        
        return query

    def is_field(self, field_title):
        for field in self.fields:
            if field.title == field_title:
                return True
        return False

def create_linked_class(table, db):
    """Given a table object and a database connection, returns a class that
    represents rows within that table, linked to the database.
    
    New objects created and modified with this class will be reflected in the database."""

    # allow lookup of row results by column name
    db.row_factory = sqlite3.Row
    
    class LinkedClass(IterableUserDict, object):

        ## Static methods for getting/setting values with the attribute interface
        # ie. obj.key = val
        def get_item_wrapper(self, key):
            def get_item_inner(self):
                return self[key]
            return get_item_inner

        def set_item_wrapper(self, key):
            def set_item_inner(self, value):
                self[key] = value
            return set_item_inner

        def del_item_wrapper(self, key):
            def del_item_inner(self):
                del self[key]
            return del_item_inner

        # register the static methods
        for field in table.fields:
            locals()[field.title] = property(fget=get_item_wrapper(None, field.title),
                                       fset=set_item_wrapper(None, field.title),
                                       fdel=del_item_wrapper(None, field.title),
                                       doc=field.title)
            
        ## Instance methods for getting/setting values with the dict interface
        # ie. obj['key'] = val
        def __getitem__(self, key):
            if not table.is_field(key):
                # not a valid key
                raise AttributeError(key)
            
            return self.data[key]

        def __setitem__(self, key, value):
            if not table.is_field(key):
                # not a valid key
                raise AttributeError(key)
            
            # update db
            c = db.cursor()
            c.execute("UPDATE %s SET %s = ? WHERE id = ?" % (table.title, key), (value, self['id']))
            c.close()

            # save
            self.data[key] = value

        def __delitem__(self, key):
            if not table.is_field(key):
                # not a valid key
                raise AttributeError(key)
            
            del self[key]

        ## Initialiser
        def __init__(self):
            self.data = {}

            # create new record in db (with default values)
            c = db.cursor()
            c.execute("INSERT INTO %s (id) VALUES (NULL)" % table.title)
            
            # save id
            self.data['id'] = c.lastrowid
            c.close()

            # load record
            self.read_sync()

        ## Sync methods
        def read_sync(self):
            """Reads the value for this ID out of the DB, replacing local values."""
            c = db.cursor()
            c.execute("SELECT * FROM %s WHERE id = ? LIMIT 1" % table.title, (self.id, ))
            row = c.fetchone()
            c.close()or field in self.fields:

            for f in table.fields:
                self.data[f.title] = row[f.title]

    return LinkedClass





if __name__ == "__main__":
    # tests
    con = sqlite3.connect(":memory:")

    title = 'exercises'
    fields = [
        Field('id', int, pk=True),
        Field('lang_id', int),
        Field('title', str),
        Field('desc', str),
        Field('solution', str),
        Field('user_id', int)
    ]

    exercises_table = Table(title, fields)

    print exercises_table.create_table_stmt()
    cur = con.cursor()
    print cur.execute(exercises_table.create_table_stmt())
    cur.close()

    Exercise = create_linked_class(exercises_table, con)
    x = Exercise()
    print x
    x['id'] = 5
    x['desc'] = 'hi'
    print x
    cur = con.cursor()
    print cur.execute("SELECT * FROM exercises").fetchall()
    cur.close()
    

