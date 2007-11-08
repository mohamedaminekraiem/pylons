from decorated import DecoratedController
from util import to_kw, from_kw
from formencode.variabledecode import variable_decode
from paste import httpexceptions

import pylons
import urlparse
import formencode


class ObjectDispatchController(DecoratedController):
    
    def _initialize_validation_context(self):
        pylons.c.form_errors = {}
        pylons.c.form_values = {}
    
    def _get_routing_info(self, url=None):
        """
        Returns a tuple (controller, remainder, params) 
        
        :Parameters:
          url
            url as string
        """
        if url is None:
            url_path = pylons.request.path_info.split('/')[1:]
        else:
            url_path = url.split('/')

        controller, remainder = object_dispatch(self, url_path)
        #XXX Place controller url at context temporarily... we should be
        #    really using SCRIPT_NAME for this.
        if remainder:
            pylons.c.controller_url = '/'.join(url_path[:-len(remainder)])
        else:
            pylons.c.controller_url = url
        if remainder and remainder[-1] == '': remainder.pop()
        return controller, remainder, pylons.request.params    
    
    def _perform_call(self, func, args):
        self._initialize_validation_context()
        controller, remainder, params = self._get_routing_info(args['url'])
        return DecoratedController._perform_call(self, controller, params, remainder=remainder)
    
    def route(self, url='/', start_response=None, **kw):
        pass


def object_dispatch(obj, url_path):
    remainder = url_path
    notfound_handlers = []
    while True:
        try:
            obj, remainder = find_object(obj, remainder, notfound_handlers)
            return obj, remainder
        except httpexceptions.HTTPNotFound, err:
            if not notfound_handlers: raise
            name, obj, remainder = notfound_handlers.pop()
            if name == 'default': return obj, remainder
            else:
                obj, remainder = obj(*remainder)
                continue


def find_object(obj, remainder, notfound_handlers):
    while True:
        if obj is None: raise httpexceptions.HTTPNotFound()
        if iscontroller(obj): return obj, remainder

        if not remainder or remainder == ['']:
            index = getattr(obj, 'index', None)
            if iscontroller(index): return index, remainder

        default = getattr(obj, 'default', None)
        if iscontroller(default):
            notfound_handlers.append(('default', default, remainder))

        lookup = getattr(obj, 'lookup', None)
        if iscontroller(lookup):
            notfound_handlers.append(('lookup', lookup, remainder))

        if not remainder: raise httpexceptions.HTTPNotFound()
        obj = getattr(obj, remainder[0], None)
        remainder = remainder[1:]
    
            
def iscontroller(obj):
    if not hasattr(obj, '__call__'): return False
    if not hasattr(obj, 'decoration'): return False
    return obj.decoration.exposed