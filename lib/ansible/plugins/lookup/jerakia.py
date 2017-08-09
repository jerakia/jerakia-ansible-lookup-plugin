import yaml
import os.path
import requests
import json

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

class Jerakia(object):
    def __init__(self,base):
        self.base = base
        self.test_var = "world"
        self.config = {}
        self.config = self.get_config()

    def get_config(self, configfile='jerakia.yaml'):
        defaults = { 'protocol': 'http', 'host': '127.0.0.1', 'port': '9843', 'version': '1', 'policy': 'default' }

        if os.path.isfile(configfile):
            data = open(configfile, "r")
            defined_config = yaml.load(data)
            combined_config = dict(defaults.items() + defined_config.items())
            return combined_config
        else:
            raise AnsibleError("Unable to find configuration file %s" % configfile)

    def lookup_endpoint_url(self, key=''):
        proto = self.config["protocol"]
        host = self.config['host']
        port = self.config['port']
        version = self.config['version']
        url = "%(proto)s://%(host)s:%(port)s/v%(version)s/lookup/%(key)s" % locals() 
        return url

    def scope(self, variables):
        scope_data = {}
        scope_conf = self.config['scope']
        hn = self.config['scope']['hostname']
        if not self.config['scope']:
            return {}
        for key, val in scope_conf.iteritems():
            metadata_entry = "metadata_%(key)s" % locals()
            scope_data[metadata_entry] = variables[val]
        return scope_data

        

    def headers(self):
        token = self.config['token']
        if not token:
            raise AnsibleError('No token configured for Jerakia')

        return {
            'X-Authentication': token
        }


    def lookup(self, key, namespace, policy='default', variables=None):
        endpoint_url = self.lookup_endpoint_url(key=key)
        namespace_str = '/'.join(namespace)
        scope = self.scope(variables)
        options = { 
            'namespace': namespace_str,
             'policy': policy,
        }

        params = dict(scope.items() + options.items())
        headers = self.headers()

        response = requests.get(endpoint_url, params=params, headers=headers)
        if response.status_code == requests.codes.ok:
          return json.loads(response.text)
        else:
          raise AnsibleError("Bad HTTP response")



class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):

         jerakia = Jerakia(self)
         ret = []

         for term in terms:
             lookuppath=term.split('/')
             key = lookuppath.pop()
             namespace = lookuppath

             if not namespace:
                 raise AnsibleError("No namespace given for lookup of key %s" % key)

             response = jerakia.lookup(key=key, namespace=namespace, variables=variables)
             ret.append(response['payload'])

         return ret

