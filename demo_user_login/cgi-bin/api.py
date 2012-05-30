#!/usr/bin/python

import sys, os
os.chdir('../spods')
sys.path.append(os.getcwd())

#from spods import *

### REMOVE BELOW CODE
from base import Field, Table
from table_linker import link_table
from json_api import handle_request, serve_api
###

import sqlite3

con = sqlite3.connect("test.db")

## SESSIONS ##
def generate_key():
    import hashlib, random
    return hashlib.sha1(str(random.random())).hexdigest()

def get_ip():
    from os import environ
    return environ.get('REMOTE_ADDR')

fields = [
    Field('id', int, pk=True),
    Field('key', str, default=generate_key),
    Field('ip', str, default=get_ip)
]
sessions_table = Table('session', fields)
Session = link_table(sessions_table, con, session_field='key', force_session=True)


## USERS ##
def encrypt_password(s):
    from hashlib import sha224
    return sha224(sha224(sha224(s).hexdigest()).hexdigest()).hexdigest()

fields = [
    Field('id', int, pk=True),
    Field('username', str),
    Field('password', str, in_mask=encrypt_password),
    Field('favourite_color', str)
]
users_table = Table('user', fields)
User = link_table(users_table, con)


## BOOKS ##
fields = [
    Field('id', int, pk=True),
    Field('title', str)
]
table = Table('book', fields)
Book = link_table(table, con)

## RELATIONS ##
Session.has_one(User)
Book.has_one(User)
User.has_one(Book)

def login(**kw):
    # we are forcing a session, so kw['_session']['session'] cannot be None
    
    if kw['_session']['session']['user']:
        # a user object already exists in this session
        raise Exception("You are already logged in.")
    
    if 'username' not in kw or 'password' not in kw:
        # a username or password was not entered
        raise Exception("Please enter your username and password.")

    matching_user = User.get_one(username=kw['username'], password=kw['password'])
    if not matching_user:
        # no user found with this user/pass combination
        raise Exception("Your username and/or password is incorrect.")

    # everything looks OK: save this user to their session object
    kw['_session']['session']['user'] = matching_user

    # their cookie doesn't need to be updated, since we didn't change the session itself
    return True

def logout(**kw):
    # we are forcing a session, so kw['_session']['session'] cannot be None
    
    if not kw['_session']['session']['user']:
        # a user object does not exist in this session
        raise Exception("You are not logged in.")

    # everything looks OK: remove the user from this session object
    kw['_session']['session']['user'] = None

    # their cookie doesn't need to be updated, since we didn't change the session itself
    return True

if __name__ == "__main__":
    print serve_api(Session, User, Book, login, logout)
    

    
