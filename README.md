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
    >>> books_table = Table('book', fields)
```
    
Now it's time to link our table to our database, and start making objects. To do this, simply connect to your database and call the `create_linked_class(table, connection)` function:
    
```python
    >>> import sqlite3
    >>> con = sqlite3.connect("database.db")
    >>> Book = spods.link_table(books_table, con)
```

Congratulations! You've just created a database, in `database.db`, and are ready to start storing `Book`s in it. SPODS will automatically create the Books table for you if it doesn't exist.

You can also add the flag `clear_existing=True` to `spods.link_table()` to delete any table already in the database with that name.

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

You can also create new objects by simply not specifying the id:

```python
    >>> book = Book(title='Atlas')
    >>> book.title
    'Atlas'
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

### Deleting records

To delete an item, just delete its primary key:

```python
    >>> del x.id; del x
```

**Warning:** Do NOT try to access an item after deleting its primary key. The safest thing to do is delete the object straight away!
    
## Syncing with the DB

All *updates*, *insertions* and *deletes* are automatically synced with the DB. So don't worry!

If, for some reason, you need to ensure the row is synced, you can manually call the sync functions:

```python
    >>> x.read_sync() # reads all values out of the DB, replacing X's local copies
    >>> x.write_sync() # writes all values into the DB, replacing the DB's values
```

## Relations

Relations in SPODS are pretty easy, too. To make a one-to-many relation, use the syntax:

```python
    >>> Book.has_one(Author)
```

where `Author` was created using the `link_table()` method, as before.

Similarly, the `has_one()` function can take the flag `clear_existing=True` to force creating a new column.

Now, you can relate two objects using their primary key:

```python
    >>> book = Book(title='Harry Potter')
    >>> author = Author(name='J K Rowling')
    >>> author.id
    1
    >>> b.author_id = 1
```

... And access each object through the other one!

```python
    >>> book['author'].name
    'J K Rowling'
    >>> book['author'].id
    1
```

**NOTE: The current version of SPODS does _NOT_ support attribute access (e.g. `b.author`, in the above example) for relationships. We are working on fixing this, but for now, only dictionary access (e.g. `b['author']`) is supported.**
    
## The JSON API

Now comes the real reason why you'd want to use SPODS. SPODS comes with a jokingly-easy, automatically generated JSON API for use in any web application.

To serve an API request, just call the `spods.serve_api` function with all the classes you want to make accessible:

```python
    >>> result = spods.serve_api(Book, Author)
    >>> result
    ...
```

`serve_api` will read the cookies and form data of the user requesting the API access, and return a string to be printed to the webpage.

<!-- The API will either return a response code of '200 OK', '400 Bad Request' or '401 Unauthorized'. -->

The resultant JSON contains 3 fields:
    * `status`, which is 0 on success, or nonzero on failure (positive on general error, negative on authorisation/permissions error)
    * `error`, which contains an error message describing the error
    * `data`, which contains a list of the objects (in dictionary format) affected by the request
        * e.g. [{"id": 2, "title": "Justice is served", "author_id": 1}, {"id": 3, "title": "The best day on Earth", "author_id": 2}]
    
API requests are in the form (`{` brackets indicate a parameter, '(' brackets indicate a default value, '[' brackets indicate an optional value):

```
    http://www.yourdomain.com/api.py?
        obj={ <table_name> }
        [&action={ (view) | add | edit | delete }]
        [&<field>={ <value> }]
        
        if action!=add:
            [&fetch={ (all) | one }]
        
        if fetch=all:
            [&start={ (0) | number >= 0 }]
            [&limit={ (<max_limit> | number >= 0 }]
```

All reserved request values (all but the ones in `<`'s) are case-insensitive. Table names, field names and field values are case-sensitive.

For the `action=edit` request, fields to _search_ for **must begin (or end) with at least one asterisk \***, whereas fields to _change_ to can stay the same.

### Editing records

For example, to rename all books called 'The Wizard of Oz' to 'The Witch of Oz', you could use:

```
    http://www.yourdomain.com/api.py?
        obj=books
        &fetch=one
        &action=edit
        &*name='The Wizard of Oz'
        &name='The Witch of Oz'
```

Equivalently, line 5 could be:

```
    &name*='The Wizard of Oz'
```

or, in fact, any of:

```
    &*name*='The Wizard of Oz'
    &***name**='The Wizard of Oz'
    &*****name****='The Wizard of Oz'
```

You get the point.

### Deleting records

To delete the book 'The Wizard of Oz', you could use:

```
    http://www.yourdomain.com/api.py?
        obj=books
        &fetch=one
        &action=delete
        &name='The Wizard of Oz'
        
```

### Viewing records

Similarly, to list all books with the author with ID 7, you could use:

```
    http://www.yourdomain.com/api.py?
        obj=books
        &fetch=all
        &action=view
        &author_id=7
```

or just:

```
    http://www.yourdomain.com/api.py?
        obj=books
        &author_id=7
```

Note that:
    * POST data is also accepted, not just GET data
        * In fact, any CGI data, in general, is accepted
    * Unrecognised parameters are ignored
    
### Working it in with jQuery

An AJAX call from jQuery (or any javascript library, really) can be setup like so:

```javascript
    $.ajax('http://www.yourdomain.com/api.py', {
        data: {
            obj: 'books', // the thing we want to get
            fetch: 'all', // how many we want
            action: 'view', // what we want to do with them
            
            // filtering parameters
            author_id: 7
        },
        success: function(json) {
            if (json.status == 0) {
                // success! do some stuff with the json
                $.each(json.data, function(i, e) {
                    alert("Book #" + i + " is called " + e.title + ".");
                });
            } else {
                // error: something went wrong on the application side
                // look at the 'error' field for details
                alert("Error: " + json.error);
            }
        },
        error: function() {
            // something went wrong altogether: connection issues, etc
            alert("Something went horribly wrong!");
        }
    });
        
```
    
## That's it!

You now know all there is to know about SPODS, and integrating it with your application.

Go make some cool software! :-)
