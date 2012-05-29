import json

MAX_LIMIT = 25

def handle_request(cookie, data, session, classes):
    """Given a list of classes, as well as the cookies, session objects and CGI form data,
    responds to the given request, returning a Python object."""

    result = { 'status': 0, 'error': '', 'data': None }

    try:

        # anything to expand?
        expandables = []
        if 'expand' in data:
            for c in data['expand'].value.split(','):
                # find this class
                for cl in classes:
                    if hasattr(cl, 'linkedclass') and cl.table.title == c:
                        # found it
                        expandables.append(cl)
                        break

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
                params['_session'] = session
                params['_expand'] = expandables

                # call function
                result['data'] = c(**params)

                # done
                return result
            elif hasattr(c, 'linkedclass') and c.table.title == data['obj'].value:
                specified_class = c
                break

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
            if data['action'].value.lower() == 'new': action = 1 # add
            if data['action'].value.lower() == 'edit': action = 2 # change
            if data['action'].value.lower() == 'delete': action = 3 # delete

        # find the fields from the remaining arguments
        # TODO: prevent fields from being called fetch, action, obj, etc
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
                # a GET or DELETE request
                field_values['_start'] = start
                field_values['_limit'] = limit
                
                # use the regular field values
                objs = specified_class.get_all(**field_values)

                if action == 3:
                    # save the rows
                    result['data'] = [dict(obj) for obj in objs]
                    
                    # delete them
                    for obj in objs:
                        del obj[specified_class.table.pk.title]
                else:
                    # expand any fields we need to
                    final_objs = []

                    # we need a nice recursive function for this
                    # (some variables are defined through closure)
                    def expand_and_serialize(o, seen=[]):
                        final_o = dict(o)
                        for expandable_class in expandables:
                            try:
                                fk_title = expandable_class.table.title
                                matched_value = o[fk_title]
                                if matched_value not in seen:
                                    final_o[fk_title] = expand_and_serialize(matched_value, seen + [o])
                            except Exception:
                                # no matched value for this expandable (or its FK)
                                continue
                        return final_o
                    
                    for o in objs:
                        final_objs.append(expand_and_serialize(o))

                    # done
                    result['data'] = final_objs
                        
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
    HTTP status response code, the cookie data, and the resulting JSON.

    args is a list of classes (representing the Linked Classes to serve) and functions
    (representing the custom functions to run).
    """

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

    # try and get session objects for any of the input classes that have session storage
    session = {}
    for c in args:
        if hasattr(c, 'linkedclass') and c.session_field:
            # try and match with cookie values
            session_value = cookie.get(c.table.title + '_' + c.session_field)
            session_obj = None
            if session_value:
                session_obj = c.get_one(**{ c.session_field: session_value.value })

            # force a new session object, if needed, and save back to the cookie
            if not session_obj and c.force_session:
                session_obj = c()
                cookie[c.table.title + '_' + c.session_field] = session_obj[c.session_field]

            # save to session vars
            session[c.table.title] = session_obj

    # get URL data
    cgi_data = FieldStorage()

    # handle request
    result = handle_request(cookie, cgi_data, session, args)
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
