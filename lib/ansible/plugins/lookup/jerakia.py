# Copyright 2017 Craig Dunn <craig@craigdunn.org>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        self.config = self.get_config()

    def config_defaults(self):
        return { 
            'protocol': 'http',
            'host': '127.0.0.1',
            'port': '9843',
            'version': '1',
            'policy': 'default'
        }

    def get_config(self, configfile='jerakia.yaml'):
        defaults = self.config_defaults()

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

    def dot_to_dictval(self, dic, key):
      key_arr = key.split('.')
      this_key = key_arr.pop(0)

      if not this_key in dic:
        raise AnsibleError("Cannot find key %s " % key)

      if len(key_arr) == 0:
        return dic[this_key]

      return self.dot_to_dictval(dic[this_key], '.'.join(key_arr))


    def scope(self, variables):
        scope_data = {}
        scope_conf = self.config['scope']
        if not self.config['scope']:
            return {}
        for key, val in scope_conf.iteritems():
            metadata_entry = "metadata_%(key)s" % locals()
            scope_value = self.dot_to_dictval(variables, val)
            scope_data[metadata_entry] = scope_value
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


# Entry point for Ansible starts here with the LookupModule class
#
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

