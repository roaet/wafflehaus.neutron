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


import requests


class BaseConnection(object):
    """Base Connection Class for calling Nova and Neutron.

       This requests wrapper mostly provides logging and a common
       framework for headers and parameters going into Requests.
    """

    def __init__(self, log=None, verify_ssl=True):
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'}
        self.log = log
        self.verify = verify_ssl

    def _make_the_call(self, method, url, body=None):
        """Note that a request response is being used here, not webob."""
        self.log.debug("%s call to %s with body = %s" % (method, url, body))
        params = {"url": url, "headers": self.headers, "verify": self.verify}
        if body is not None:
            params["data"] = body
        func = getattr(requests, method.lower())
        try:
            resp = func(**params)
        except Exception as e:
            self.log.error("Call to %s failed with %s: %s" % (url, repr(e),
                                                              e.message))
            return None, e
        else:
            self.log.debug("Call to %s returned with status %s and body "
                           "%s" % (url, resp.status, resp.text))
        return resp.status_code, resp.json()

    def delete(self, url, body):
        status, resp = self._make_the_call("DELETE", url, body)
        return status, resp

    def get(self, url, body=None):
        status, resp = self._make_the_call("GET", url, body)
        return status, resp

    def post(self, url, body):
        status, resp = self._make_the_call("POST", url, body)
        return status, resp

    def put(self, url, body):
        status, resp = self._make_the_call("PUT", url, body)
        return status, resp


class NovaConnection(BaseConnection):
    """This connection type is primarily for admin-virtual-interfaces.

       However! It can easily be expanded for more...

       Example admin-virtual-interface call:

       https://<nova>:8774/v2/<tenant_id>/servers/<instance id>/
                          admin-virtual-interfaces/<port uuid>

       Payload:

        {"virtual_interface":
           {"action":"delete",
            "network_id": "040e3576-2d44-4984-8578-d6b82f2a524f",
            "fixed_ips": [{"subnet_id": "",
                           "ip_address": ""}],
            "id": "7d154734-e669-4608-bef6-ad6f205c6891",
            "address": "BC:76:4E:11:59:5C"}}

       Example os-virtual-interface call:

       https://<nova>:8774/servers/<instance_id>/os-virtual-interfacesv2

       Payload:

        {"virtual_interface":
            {"network_id": "<network_id>"}}
    """

    def __init__(self, log=None, port=None, url=None, verify_ssl=True):
        super(NovaConnection, self).__init__(log=log, verify_ssl=verify_ssl)
        self.url = "%s:%d" % (url, port) if self.port is not None else url

    def admin_virtual_interfaces(self, action=None, address=None,
                                 fixed_ips=None, network_id=None,
                                 port_id=None, tenant_id=None,
                                 instance_id=None):
        body = {"virtual_interface":
                {"action": action,
                 "address": address,
                 "fixed_ips": fixed_ips,
                 "id": port_id,
                 "network_id": network_id}}
        url = "%s/v2/%s/servers/%s/admin-virtual-interfaces/%s/" % (
            self.url, tenant_id, instance_id, port_id)

        status, nova_resp = self.put(url, body)
        return status, nova_resp

    def os_virtual_interfaces(self, network_id=None):

        body = {"virtual_interface":
                {"network_id": network_id}}

        status, nova_resp = self.put(self.url, body)
        return status, nova_resp


class NeutronConnection(BaseConnection):
    """Use this connection type for any Neutron Calls.

       Currently it's for pulling /port info, but may be expanded
       later when more work is done on /ip_addresses.

       Example /ports call:

       curl -X GET neutron://v2.0/ports/<id>
    """

    def __init__(self, log=None, port=None, url=None, verify_ssl=True):
        super(NeutronConnection, self).__init__(log=log, verify_ssl=verify_ssl)
        self.url = "%s:%d" % (url, port) if self.port is not None else url

    def ip_addresses(self):
        """Placeholder for ip_addresses info call."""
        pass

    def ports(self, port_id=None):
        url = "%s/v2.0/ports/%s/" % (self.url, port_id)
        status, neutron_resp = self.get(url)
        return status, neutron_resp
