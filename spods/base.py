import json

blank_fn = lambda s: s

# TODO: this is duplicately defined in table_linker. Put them both in a common include
is_function = lambda f: hasattr(f, '__call__')

class Field(object):
    """The class representing a single field in a table."""
    
    type_map = {
        str: ("TEXT", str),
        int: ("INTEGER", int),
        bool: ("INTEGER", lambda x: {True: 1, False: 0}[x]),
        tuple: ("TEXT", json.dumps)
    }
    
    def __init__(self, title, python_type=None, null=None, default=None, pk=None, fk=None, in_mask=blank_fn, out_mask=blank_fn):
        """Creates a new field object.

* title is the name for this field
* python_type is the corresponding python type for this field (e.g. str)
* null is whether the field can be null or not (e.g. False)
* default is the default value for this field (can be a value or a function, e.g. time.time - if it is a function, it is called with no arguments)
* pk is whether the field is a pk or not (e.g. True)
* fk is the class for which this is a fk (e.g. None, or Person)
* in_mask is a function (single-parameter) which is applied when data is about to be stored in the DB
* out_mask is a function (single-parameter) which is applied when data has been retrieved from the DB
"""
        
        for c in title:
            if c.lower() not in 'abcdefghijklmnopqrstuvwxyz' + '0123456789' + '_':
                raise Exception("Field name contains invalid characters.")
        
        self.title = title
        self.python_type = python_type
        self.null = null
        self.default = default
        self.pk = pk
        self.fk = fk

        self.in_mask = in_mask
        self.out_mask = out_mask

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
        if field.default != None and not is_function(field.default):
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

    def field_map(self):
        return dict((f.title, f) for f in self.fields)

    def get_field(self, field_title):
        for field in self.fields:
            if field.title == field_title:
                return field
        return None
