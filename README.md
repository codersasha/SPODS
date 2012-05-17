# Simple Python Object-Database Serialiser (SPODS)

## Why it rocks

Databases are annoying. Sometimes, we just want to save persistent data, and not
have to worry about SQL injection, transaction issues, and connection problems.

With SPODS, there is finally an alternative. SPODS is a simple, lightweight, easy to use alternative to heavy serialisation libraries. SPODS also provides a great way to access generic Python objects.

## Getting started

First, copy spods.py to the directory you want to use it in.
Include it using:
    
```python
    >>> import spods
```

## Making SPODS objects

Since the Python class constructor is not _really_ useful to use here, we will use a different method of defining a class.

First, create a bunch of `Field` objects and store them in a `Table`:

```python
    >>> fields = [
    ...     Field('id', int, pk=True),
    ...     Field('title', str),
    ...     Field('isbn', int),
    ...     Field('condition', bool)
    ... ]
    ... 
    >>> books_table = Table('books', fields)
```
    
Now it's time to link our table to our database, and start making objects. To do this, simply connect to your database and call the `create_linked_class(table, connection)` function:
    
```python
    >>> import sqlite3
    >>> con = sqlite3.connect("database.db")
    >>> Book = link_table(books_table, con)
```

Congratulations! You've just created a database, in `database.db`, and are ready to start storing `Book`s in it. SPODS will automatically create the Books table for you if it doesn't exist.

To add your first record, you can run something like:

```python
    >>> book = Book()
    >>> book
    {'id': 1, 'title': None, 'isbn': None, 'condition': None}
```

Now, when you modify your `book` variable, the changes will be reflected in your database.

You can also access an existing book object by providing its ID:

```python
    >>> book.title = 'The Notebook'
    >>> book.title
    'The Notebook'
    >>> existing_book = Book(id=1)
    >>> existing_book
    {'id': 1, 'title': 'The Notebook', 'isbn': None, 'condition': None}
```

## Using SPODS objects

You can use all the usual getter and setter methods for attributes, such as:
    
```python
    >>> x.id = 7
    >>> x.id
    7
```
    
As well as dictionary-like access:

```python
    >>> x['id'] = 7
    >>> x['id']
    7
```
    
Or a mix of both:

```python
    >>> field = 'id'
    >>> x[field] = 7
    >>> x.id
    7
```
    
You can also reset fields to their default values, using the `del` keyword:
    
```python
    >>> x['id'] = 5
    >>> del x['id']
    >>> x['id'] == None
    True
```

Or, equivalently:

```python
    >>> x.id = 5
    >>> del x.id
    >>> x.id == None
    True
```
    
## Syncing with the DB

All *updates*, *insertions* and *deletes* are automatically synced with the DB. So don't worry!

If, for some reason, you need to ensure the row is synced, you can manually call the sync functions:

```python
    >>> x.read_sync() # reads all values out of the DB, replacing X's local copies
    >>> x.write_sync() # writes all values into the DB, replacing the DB's values
```
    
## That's it!

Go make some cool software! :-)
