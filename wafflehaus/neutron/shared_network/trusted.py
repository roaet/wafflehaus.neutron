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

import webob.dec

from wafflehaus.base import WafflehausBase
import wafflehaus.resource_filter as rf


class TrustedSharedNetwork(WafflehausBase):

    def __init__(self, app, conf):
        super(TrustedSharedNetwork, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)
        self.log.info('Starting wafflehaus trusted shared nets middleware')
        self.resource = conf.get('resource', 'GET /v2.0/networks{.format}')
        self.resources = rf.parse_resources(self.resource)

        self.trusted_nets = set(conf.get('trusted', []))

    def _shared_nets_filter(self, req):
        if "shared" not in req.GET:
            return self.app
        return self._sanitize_shared_nets(req)

    def _sanitize_shared_nets(self, req):
        headers = req.headers
        response = req.get_response(self.app)
        body = response.json
        networks = body.get('networks')

        whitelist = set(headers.get('X_NETWORK_WHITELIST', '').split(','))
        blacklist = set(headers.get('X_NETWORK_BLACKLIST', '').split(','))

        # Collect the shared network ids
        shared_nets = set(n['id'] for n in networks if n['shared'])

        # Collect the unshared network ids
        unshared_nets = set(n['id'] for n in networks if not n['shared'])

        # Only allow configured or whitelisted shared networks
        # But definitely remove blacklisted networks
        okay_nets = set(n for n in shared_nets if n in
                        whitelist.union(self.trusted_nets) - blacklist)

        # Use the networks that are either ok or unshared
        body['networks'] = [n for n in networks if n['id'] in
                            okay_nets.union(unshared_nets)]
        response.json = body

        return response

    @webob.dec.wsgify
    def __call__(self, req):
        if not self.enabled:
            return self.app
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
