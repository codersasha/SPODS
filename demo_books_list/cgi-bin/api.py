#!/usr/bin/python

import sys
sys.path.append("C:/Users/Sasha/Dropbox/Programming/Python MySQL Serializer/spods/")

#from spods import *

### REMOVE BELOW CODE
from base import Field, Table
from table_linker import link_table
from json_api import handle_request, serve_api
###

import sqlite3

con = sqlite3.connect("test.db")

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

def check_credit(**kw):
    if 'credit_card' not in kw or not kw['credit_card'].isdigit():
        raise Exception("Please enter a valid credit card number.")
    credit_sum = 0
    for digit in kw['credit_card']:
        credit_sum += int(digit)
    return {'sum': credit_sum}

if __name__ == "__main__":
    print serve_api(Book, Person, check_credit)
    

    
