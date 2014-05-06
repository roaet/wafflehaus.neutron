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
import webob.dec

from wafflehaus.base import WafflehausBase
import wafflehaus.resource_filter as rf


class TrustedSharedNetwork(WafflehausBase):

    def __init__(self, app, conf):
        super(TrustedSharedNetwork, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)
        self.log.info('Starting wafflehaus trusted shared nets  middleware')
        self.testing = (conf.get('testing') in
                        (True, 'true', 't', '1', 'on', 'yes', 'y'))
        self.resource = conf.get('resource', 'GET /v2.0/networks{.format}')
        self.resources = rf.parse_resources(self.resource)

        self.trusted_nets = conf.get('trusted', [])

    def _shared_nets_filter(self, req):
        if "shared" not in req.GET:
            return self.app
        return self._sanitize_shared_nets(req)

    def _sanitize_shared_nets(self, req):
        headers = req.headers
        response = req.get_response(self.app)
        body_json = json.loads(response.body)
        networks = body_json.get("networks")
        deleted_networks = []

        whitelist = headers.get('X_NETWORK_WHITELIST', '')
        whitelist = whitelist.split(',')

        blacklist = headers.get('X_NETWORK_BLACKLIST', '')
        blacklist = blacklist.split(',')

        for net in networks:
            id = net.get('id')
            if id in blacklist:
                deleted_networks.append(net)
            elif id in self.trusted_nets:
                continue
            elif net.get('shared') is True and id not in whitelist:
                deleted_networks.append(net)

        for del_net in deleted_networks:
            networks.remove(del_net)

        response.body = json.dumps(body_json)

        return response

    @webob.dec.wsgify
    def __call__(self, req):
        if self.testing or not rf.matched_request(req, self.resources):
            return self.app
        return self._shared_nets_filter(req)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def trusted_shared_nets(app):
        return TrustedSharedNetwork(app, conf)
    return trusted_shared_nets
