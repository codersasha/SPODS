#!/usr/bin/python

# use SQLite for now
import sqlite3
import json

from UserDict import IterableUserDict

class Field(object):
    """The class representing a single field in a table."""
    
    type_map = {
        str: ("TEXT", str),
        int: ("INTEGER", int),
        bool: ("INTEGER", lambda x: {True: 1, False: 0}[x]),
        tuple: ("TEXT", json.dumps)
    }
    
    def __init__(self, title, python_type=None, null=None, default=None, pk=None, fk=None):
        for c in title:
            if c.lower() not in 'abcdefghijklmnopqrstuvwxyz' + '0123456789' + '_':
                raise Exception("Field name contains invalid characters.")
        
        self.title = title
        self.python_type = python_type
        self.null = null
        self.default = default
        self.pk = pk
        self.fk = fk

        self.sql_type = None
        self.type_converter = None
        if self.python_type != None:
            self.sql_type = self.type_map[self.python_type][0]
            self.type_converter = self.type_map[self.python_type][1]

    def __str__(self):
        return self.title

class Table(object):
    """The class representing an unlinked table.

    A table consists of 1 or more fields, and exactly one primary key."""
    
    def __init__(self, title, fields=[]):
        self.title = title
        self.fields = fields

        # create the ID field, if no primary key was specified
        for f in fields:
            if f.pk == True:
                self.pk = f
                break
        else:
            # no fields are PK
            self.pk = Field('id', int, pk=True)
            fields.append(self.pk)

    @staticmethod
    def field_stmt(field):
        query = ""
        
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

        return query

    def delete_table_stmt(self, force=False):
        if force:
            query = "DROP TABLE %s" % self.title
        else:
            query = "DROP TABLE IF EXISTS %s" % self.title

        return query

    def create_table_stmt(self, force=False):
        if force:
            query = "CREATE TABLE %s (" % self.title
        else:
            query = "CREATE TABLE IF NOT EXISTS %s (" % self.title

        for field in self.fields:
            query += Table.field_stmt(field)

            # 5. comma
            query += " ,"

        # remove last comma
        query = query[:-1]
        query += ")"
        
        return query
    
    def add_field_stmt(self, new_field):
        query = "ALTER TABLE %s ADD COLUMN " % (self.title)
        query += Table.field_stmt(new_field)
        return query
        
    def is_field(self, field_title):
        for field in self.fields:
            if field.title == field_title:
                return True
        return False

    def is_pk(self, field_title):
        for field in self.fields:
            if field.title == field_title:
                if field.pk:
                    return True
                return False
        return False

    def fks(self):
        return [x for x in self.fields if x.fk]

def link_table(table, db, clear_existing=False):
    """Given a table object and a database connection, returns a class that
    represents rows within that table, linked to the database.
    
    New objects created and modified with this class will be reflected in the database.

    If clear_existing is True, deletes the table (if it exists) before linking it.
    """

    # helper functions that, through closure, are specific to this table
    def run_query(query, replacements=tuple()):
        """Opens a cursor and runs a query. Does not return anything."""
        cur = db.cursor()
        cur.execute(query, replacements)
        # cur.commit()
        cur.close()

    # allow lookup of row results by column name
    db.row_factory = sqlite3.Row

    # turn on autocommits
    con.isolation_level = None

    # clear the table, if we want
    if clear_existing:
        run_query(table.delete_table_stmt(force=False))

    # attempt to make the table, if it doesn't already exist
    run_query(table.create_table_stmt(force=False))
    
    class LinkedClass(IterableUserDict, object):
        """The class representing a dynamically-linked object.

        Each object created with this class is linked to the database table."""

        # save the table object to thisClass.table
        locals()['table'] = table

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
                # not a field... but is it one of the FKs?
                # check if it's a known foreign key in this table
                for field in table.fks():
                    # TODO: this comparison is iffy; if a table name has an underscore in it, this won't match the table's FK correctly
                    foreign_table_name = field.title.split('_')[0]
                    if foreign_table_name == key:
                        # yup, its this FK: get the matching attribute
                        foreign_table_pk_name = field.fk.table.pk.title
                        fk = self.data[foreign_table_name + '_' + foreign_table_pk_name]

                        if fk == None:
                            # not linked to anything
                            return None

                        # get the matching object
                        obj = field.fk(**{foreign_table_pk_name: fk })

                        return obj
                
                # not a valid key
                raise AttributeError(key)
            
            return self.data[key]

        def __setitem__(self, key, value):
            if not table.is_field(key):
                # not a valid key
                # TODO: not working?
                raise AttributeError(key)
            
            # update db & save
            run_query("UPDATE %s SET %s = ? WHERE %s = ?" % (table.title, key, table.pk.title), (value, self.id))
            self.data[key] = value

        def __delitem__(self, key):
            if not table.is_field(key):
                # not a valid key
                raise AttributeError(key)

            # is this the PK? If so, delete the record
            if table.is_pk(key):
                run_query("DELETE FROM %s WHERE %s = ?" % (table.title, table.pk.title), (self.id, ))
            else:
                run_query("UPDATE %s SET %s = NULL WHERE %s = ? LIMIT 1" % (table.title, key, table.pk.title), (self.id, ))

            # either way, set the key to none
            self[key] = None

        ## Initialiser
        def __init__(self, **kw):
            """Creates a new instance of this object, linked to the database.
            All modifications are synced.

            Database values can be optionally passed to the constructor, which will be passed into the db.

            If the primary key is provided, loads this existing record, rather than creating a new one."""
            
            self.data = {}

            if table.pk.title not in kw:
                # create new record in db (with default values)
                c = db.cursor()
                c.execute("INSERT INTO %s (%s) VALUES (NULL)" % (table.title, table.pk.title))
                
                # save id
                self.data[table.pk.title] = c.lastrowid
                c.close()
            else:
                # load existing record
                self.data[table.pk.title] = kw[table.pk.title]

            # load record
            self.read_sync()

            # save initialised values
            # TODO: do this with a query, in a single DB call, in the INSERT statement above
            for k in kw:
                if table.is_field(k):
                    self[k] = kw[k]

        ## Sync methods
        def read_sync(self):
            """Reads the value for this row out of the DB, replacing local values.
            Relies on the ID of the object to match the data in the DB."""
            
            c = db.cursor()
            c.execute("SELECT * FROM %s WHERE id = ? LIMIT 1" % table.title, (self.id, ))
            row = c.fetchone()
            c.close()

            if row == None:
                raise Exception("No record found with ID '%s'." % self.id)
                
            for f in table.fields:
                self.data[f.title] = row[f.title]

        def write_sync(self):
            """Writes the value for this row into the DB, replacing all values.
            Relies on the ID of the object to match the data in the DB."""

            # build up query
            query = "UPDATE %s SET " % (table.title)
            args = []
            for f in table.fields:
                query += " %s = ?," % (f.title)
                args.append(self[f.title])
            # remove last comma
            query = query[:-1] + " WHERE id = ?"
            args.append(self['id'])
            
            run_query(query)

        @staticmethod
        def get_one(**kw):
            """Returns a single object from the DB that matches the given criteria, or None if no objects were found.

            **kw is a dictionary of field --> value criteria.

            Some reserved values are:
                * _start, which is ignored
                * _limit, which is ignored
                * _order, which specifies the field to order by
                * _reverse, which specifies ascending (False) or desending (True) for the ordering
            """
            # TODO: prevent fields from being called _start, _limit, _order, _reverse, etc (the reserved values)

            kw['_start'] = 0
            kw['_limit'] = 1

            objs = LinkedClass.get_all(**kw)
            if objs:
                return objs[0]
            return None

        @staticmethod
        def get_all(**kw):
            """Returns a list of objects from the DB that match the given criteria.

            **kw is a dictionary of field --> value criteria.

            Some reserved values are:
                * _start, which specifies the starting offset
                * _limit, which specifies the number of records to return
                * _order, which specifies the field to order by
                * _reverse, which specifies ascending (False) or desending (True) for the ordering
            
            """
            # TODO: prevent fields from being called _start, _limit, etc (the reserved values)

            # build up qualifiers for the WHERE clause
            query_clause = ""
            query_args = []
            for k in kw:
                if table.is_field(k):
                    if query_clause:
                        query_clause += " AND "

                    # treat 'None' differently
                    if kw[k] == None:
                        query_clause += " %s IS NULL " % (k)
                    else:
                        query_clause += " %s = ? " % (k)
                        query_args.append(kw[k])

            # search to get primary keys
            query = "SELECT %s FROM %s " % (table.pk.title, table.title)
            if query_clause:
                query += " WHERE "
                query += query_clause

            # was start/limit specified?
            if '_start' in kw and '_limit' in kw:
                query += " LIMIT %s, %s " % (kw['_start'], kw['_limit'])
            elif '_limit' in kw:
                query += " LIMIT %s " % kw['_limit']

            # was an ordering specified?
            if '_order' in kw:
                query += " ORDER BY %s " % (kw['_order'])
                if '_reverse' in kw:
                    query += " %s " % ('DESC' if kw['_reverse'] else 'ASC')

            # run query
            c = db.cursor()
            c.execute(query, tuple(query_args))
            
            # build objects
            # TODO: could make an offline object system, to prevent the N calls that are about to happen in our DB
            objs = []
            for row in c:
                pk = row[table.pk.title]
                objs.append(LinkedClass(**{ table.pk.title: pk }))
                
            # clean up
            c.close()
            return objs
            
        @staticmethod
        def has_one(class_var, new_field_name = None, clear_existing = False):
            """Creates ownership of this class over another class.

            e.g. X.has_one(Y) means each instance of X has at most one instance of Y.

            class_var should be an instance of LinkedClass (created from the link_table() function)."""

            # set default new field name to 'table_id'
            if new_field_name == None:
                new_field_name = class_var.table.title + "_"
                
                # get PK of this table (e.g. ID) and add it to new field name
                new_field_name += table.pk.title

            new_field = Field(new_field_name, int, fk=class_var)

            # add the field to the DB
            try:
                run_query(table.add_field_stmt(new_field))

            except sqlite3.OperationalError:
                
                # column already exists
                if clear_existing:
                    # delete column and run it again
                    # TODO
                    pass

            # add column to all new object instances
            table.fields.append(new_field)

    return LinkedClass

MAX_LIMIT = 25

def handle_request(cookie, data, classes):
    """Given a list of classes, as well as the cookies and CGI form data,
    responds to the given request, returning a Python object."""

    result = { 'status': 0, 'error': '', 'data': None }

    try:

        # check they specified an object
        if 'obj' not in data:
            result['status'], result['error'] = (1, 'No objects specified.')
            return result

        # get the class they specified
        specified_class = None
        for c in classes:
            if c.__name__ == data['obj'].value:
                # custom function

                # get other URL params
                params = {}
                for field in data:
                    params[field] = data[field].value

                # send special params
                params['_cookie'] = cookie
                params['_classes'] = classes

                # call function
                result['data'] = c(**params)

                # done
                return result
            else:
                try:
                    if c.table.title == data['obj'].value:
                        specified_class = c
                        break
                except:
                    continue

        if specified_class == None:
            # no class found
            result['status'], result['error'] = (1, 'Invalid object specified.')
            return result

        # build up the options
        if 'fetch' in data and data['fetch'].value.lower() == 'one':
            # fetch one
            start = 0
            limit = 1
        else:
            # fetch all
            start = 0
            limit = MAX_LIMIT
            if 'start' in data and data['start'].value.isdigit() and int(data['start'].value) >= 0:
                start = int(data['start'].value)
            if 'limit' in data and data['limit'].value.isdigit() and int(data['limit'].value) >= 0:
                limit = int(data['limit'].value)
            
        action = 0 # view
        if 'action' in data:
            if data['action'].value.lower() == 'add': action = 1 # add
            if data['action'].value.lower() == 'edit': action = 2 # change
            if data['action'].value.lower() == 'delete': action = 3 # delete

        # find the fields from the remaining arguments
        # TODO: prevent fields from being called fetch, action or obj
        field_values = {}
        field_search_values = {}
        for field in data:
            if specified_class.table.is_field(field):
                field_values[field] = data[field].value
            elif specified_class.table.is_field(field.strip('*')):
                field_search_values[field.strip('*')] = data[field].value

        # perform the specified action
        if action == 1:
            # we're adding: get the fields together and build the object
            new_obj = specified_class(**field_values)
            result['data'] = [dict(new_obj)]

        else:
            # we need to get the objects to modify

            if action != 2:
                field_values['_start'] = start
                field_values['_limit'] = limit
                
                # use the regular field values
                objs = specified_class.get_all(**field_values)
                result['data'] = [dict(obj) for obj in objs]

                if action == 3:
                    # delete the rows
                    for obj in objs:
                        del obj[specified_class.table.pk.title]
            else:
                field_search_values['_start'] = start
                field_search_values['_limit'] = limit
                
                # use the asterisked fields for searching...
                objs = specified_class.get_all(**field_search_values)

                # ...and the regular fields for modifying
                for obj in objs:
                    for field in field_values:
                        obj[field] = field_values[field]

                # done
                result['data'] = [dict(obj) for obj in objs]

    except Exception, e:
        result['status'], result['error'] = 2, "%s: %s" % (type(e).__name__, str(e))

    return result

def serve_api(*args):
    """Given a list of LinkedClasses, reads the cookies and form data from the user and
    tries to perform the specified request.

    Returns a string, representing the content to print to the screen, which includes the
    HTTP status response code, the cookie data, and the resulting JSON."""

    from os import environ
    from cgi import FieldStorage
    from Cookie import SimpleCookie
    from json import dumps

    # TODO: remove this (for debugging only)!
    from cgitb import enable as enable_debug; enable_debug()

    # get cookies
    cookie = SimpleCookie()
    cookie_string = environ.get('HTTP_COOKIE')
    if cookie_string:
        cookie.load(cookie_string)

    # get URL data
    cgi_data = FieldStorage()

    # handle request
    result = handle_request(cookie, cgi_data, args)
    status = result.get('status', 1)

    # return appropriate response
    response = ""
    if cookie: response += str(cookie)

    # TODO: get the status to return appropriately: is this possible as a CGI script?
    # response += 'Status: '
    # if status > 0: response += '400 Bad Request\r\n'
    # if status < 0: response += '401 Unauthorized\r\n'
    # se: response += '200 OK\r\n'
    
    response += "Content-Type: application/JSON\r\n\r\n"
    if result: response += dumps(result)

    return response
