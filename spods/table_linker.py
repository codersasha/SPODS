# use SQLite for now
import sqlite3

from UserDict import IterableUserDict

from base import Field, Table

# TODO: this is duplicately defined in base. Put them both in a common include
is_function = lambda f: hasattr(f, '__call__')

def link_table(table, db, clear_existing=False, session_field=None, force_session=False):
    """Given a table object and a database connection, returns a class that
    represents rows within that table, linked to the database.
    
    New objects created and modified with this class will be reflected in the database.

    If clear_existing is True, deletes the table (if it exists) before linking it.


    The following parameters apply during the API stage:

    If session_field is a string, the value of that field in the table is stored in
    the user's cookie. It must be unique, as it is used as a discriminator to find the
    matching record in the table when a user's cookie is detected.

    If force_session is True, a new object is created if no matching object is found
    for a particular user's session, and that session is saved to that user.
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
    db.isolation_level = None

    # clear the table, if we want
    if clear_existing:
        run_query(table.delete_table_stmt(force=False))

    # attempt to make the table, if it doesn't already exist
    run_query(table.create_table_stmt(force=False))
    
    class LinkedClass(IterableUserDict, object):
        """The class representing a dynamically-linked object.

        Each object created with this class is linked to the database table."""

        # save the objects & parameters to this class
        locals()['table'] = table
        locals()['session_field'] = session_field
        locals()['force_session'] = force_session

        # a hack to tell that this is a linked class
        locals()['linkedclass'] = True

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
                    # TODO: this comparison is iffy; if a primary key has an underscore in it, this won't match the table's FK correctly
                    foreign_table_name = field.title.split('_')[0]
                    if foreign_table_name == key:
                        # yup, its this FK: get the matching attribute
                        foreign_table_pk_name = field.fk.table.pk.title
                        fk = self.data[foreign_table_name + '_' + foreign_table_pk_name]

                        if not fk:
                            # not linked to anything
                            return None

                        # get the matching object
                        obj = field.fk(**{foreign_table_pk_name: fk })

                        return obj
                
                # not a valid key
                raise AttributeError(key)

            # apply any out masks, and return
            val = self.data[key]
            return table.get_field(key).out_mask(val)

        def __setitem__(self, key, value):
            # check if we're assigning to an item
            if not table.is_field(key):
                # not a valid key

                # check if we're assigning to a FK
                for field in self.table.fks():
                    if field.fk.table.title == key:
                        # this is a potentially matching field
                        foreign_pk_field = field.fk.table.pk.title
                        local_fk_field = field.title

                        # is this a valid link? (e.g. x['book'] is going to be stored in table 'book')
                        if value != None and key != type(value).table.title:
                            raise AttributeError(str(key) + " is not a valid type for table " + type(value).table.title)

                        # overwrite the foreign key, either with 0 or with the corresponding PK value
                        if value == None:
                            self[local_fk_field] = 0
                        else:
                            self[local_fk_field] = value[foreign_pk_field]

                        # done
                        return
                        
                # no match found
                raise AttributeError(key)
                return

            # apply any in masks
            new_value = table.get_field(key).in_mask(value)
            
            # update db & save
            run_query("UPDATE %s SET %s = ? WHERE %s = ?" % (table.title, key, table.pk.title), (new_value, self[table.pk.title]))
            self.data[key] = new_value

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

            # save initialised values (and defaults, for non-initialised values)
            # TODO: do this with a query, in a single DB call, in the INSERT statement above
            for field in table.fields:
                if field.title in kw:
                    self[field.title] = kw[field.title]
                elif field.default and table.pk.title not in kw:
                    # making a new record: save defaults
                    if not is_function(field.default):
                        self[field.title] = field.default
                    elif field.default and is_function(field.default):
                        self[field.title] = field.default()

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
                        query_args.append(table.get_field(k).in_mask(kw[k]))

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
