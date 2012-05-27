#!/usr/bin/python

from main import *
import sqlite3

con = sqlite3.connect(":memory:")

fields = [
    Field('id', int, pk=True),
    Field('title', str),
    Field('isbn', str),
    Field('condition', str)
]
books_table = Table('book', fields)
Book = link_table(books_table, con)

fields = [
    Field('id', int, pk=True),
    Field('name', str),
    Field('age', int),
    Field('happy', bool)
]
people_table = Table('person', fields)
Person = link_table(people_table, con)

Person.has_one(Book)

person = Person()
book = Book()
    

    
