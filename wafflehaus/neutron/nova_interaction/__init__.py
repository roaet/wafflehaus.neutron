# Copyright 2013 Openstack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from webob.dec import wsgify
from webob import Response

from wafflehaus.base import WafflehausBase
from wafflehaus.neutron.nova_interaction.common import (NeutronConnection as
                                                        NeutronConn)
from wafflehaus.neutron.nova_interaction.common import (NovaConnection as
                                                        NovaConn)
import wafflehaus.resource_filter as rf


class NovaInteraction(WafflehausBase):
    def __init__(self, app, conf):
        super(NovaInteraction, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)
        self.log.info('Starting wafflehaus nova_callback middleware')
        self.neutron_port = conf.get('neutron_port')
        self.neutron_url = conf.get('neutron_url')
        self.neutron_verify_ssl = conf.get('neutron_verify_ssl', True)
        self.nova_port = conf.get('nova_port')
        self.nova_url = conf.get('nova_url')
        self.nova_verify_ssl = conf.get('nova_verify_ssl', True)
        self.resources = rf.parse_resources(conf.get('resources'))

    def _process_call(self, req, resource):
        """This is were all callbacks are made and the req is processed."""
        if resource == "ports":
            if req.method.upper() in ('PUT', 'POST'):
                # Pass the request back to be processed by other filters
                #   and Neutron first
                resp = req.get_response(self.app)
                if resp.status_code not in (200, 204):
                    return resp
                resp_body = resp.json

                # Variables for Nova Call, obtained from Neutron response
                action = "create"
                address = resp_body['port']['mac_address']
                fixed_ips = resp_body['port']['fixed_ips']
                instance_id = resp_body['port']['instance_id']
                network_id = resp_body['port']['network_id']
                port_id = resp_body['port']['id']
                tenant_id = resp_body['port']['tenant_id']

            elif req.method.upper() == "DELETE":
                action = "delete"
                port_id = req.path.split("/")
                port_id = port_id[port_id.index("ports") + 1]

                # DELETEs do not have all the port info that we need, so a
                # call to Neutron must be made first.
                neutron_conn = NeutronConn(log=self.log,
                                           port=self.neutron_port,
                                           url=self.neutron_url,
                                           verify_ssl=self.neutron_verify_ssl)
                status, neutron_resp = neutron_conn.ports(port_id=port_id)
                if isinstance(neutron_resp, Exception):
                    return neutron_resp
                elif status not in (200, 204):
                    resp = Response()
                    resp.status = 500
                    new_body = {"neutron_callback":
                                {"port_id": port_id,
                                 "status": "error",
                                 "error": neutron_resp}}
                    resp.body = json.dumps(new_body)
                    return resp

                # Now that we have the port info, we can make the variables
                # for the Nova Call
                address = neutron_resp['port']['mac_address']
                fixed_ips = neutron_resp['port']['fixed_ips']
                instance_id = neutron_resp['port']['instance_id']
                network_id = neutron_resp['port']['network_id']
                tenant_id = neutron_resp['port']['tenant_id']

                # Port info saved, now send the request back to processed by
                #   other filters and Neutron
                resp = req.get_response(self.app)
                if resp.status_code not in (200, 204):
                    return resp
                else:
                    new_body = resp.json
                    new_body['neutron_callback'] = {"port_id": port_id,
                                                    "status": "success"}
                    resp.body = json.dumps(new_body)

            nova_conn = NovaConn(log=self.log, url=self.nova_url,
                                 verify_ssl=self.nova_verify_ssl)
            status, nova_resp = nova_conn.admin_virtual_interfaces(
                action=action, address=address, fixed_ips=fixed_ips,
                network_id=network_id, port_id=port_id, tenant_id=tenant_id,
                instance_id=instance_id)
            if isinstance(nova_resp, Exception):
                return nova_resp
            elif status not in (200, 204):
                # We'll likely want to provide the customer with a call here
                # such as virtual-interface-delete/virtual-interface-update
                resp.status = 500
                new_body = resp.json
                new_body['nova_callback'] = {"instance_id": instance_id,
                                             "status": "error",
                                             "error": nova_resp}
                resp.body = json.dumps(new_body)
            else:
                new_body = resp.json
                new_body['nova_callback'] = {"instance_id": instance_id,
                                             "status": "success"}
                resp.body = json.dumps(new_body)
            return resp
        elif resource == "ip_addresses":
            pass  # Insert logic to call Nova for ip_addresses changes here
        return resp

    @wsgify
    def __call__(self, req):
        """This returns an app if ignored or a response if processed."""
        super(NovaInteraction, self).__call__(req)
        if not self.enabled:
            return self.app
        if rf.matched_request(req, self.resources):
            req_path = req.path.lower()
            if "/ports" in req_path:
                resource = "ports"
            elif "/ip_addresses" in req_path:
                resource = "ip_addresses"
            resp = self._process_call(req, resource)
            return resp
        return self.app


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def wrapper(app):
        return NovaInteraction(app, conf)

    return wrapper
