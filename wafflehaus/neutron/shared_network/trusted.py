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
        self.resource = conf.get('resource', 'GET /v2.0/networks{.format}')
        self.resources = rf.parse_resources(self.resource)

        self.trusted_nets = conf.get('trusted', '')
        if isinstance(self.trusted_nets, basestring):
            self.trusted_nets = self.trusted_nets.split()
        self.trusted_nets = set(self.trusted_nets)

    def _shared_nets_filter(self, req):
        tenant_id = req.headers.get('X_TENANT_ID')
        user_id = req.headers.get('X_USER_ID')
        if "shared" not in req.GET:
            self.log.info('Checking for shared nets filter. '
                          'Shared not in get request '
                          'tenant_id %s user_id %s' % (tenant_id, user_id))
            return self.app
        return self._sanitize_shared_nets(req)

    def _sanitize_shared_nets(self, req):
        context_dict = req.environ.get('neutron.context')
        if context_dict:
            self.log.info('_check_basics, Neutron Context : ' +
                          'request id %s, project id %s, '
                          'tenant name %s, is admin %s, user id %s'
                          % (str(context_dict.request_id),
                             str(context_dict.project_id),
                             str(context_dict.tenant_name),
                             str(context_dict.is_admin),
                             str(context_dict.user_id)))
        tenant_id = req.headers.get('X_TENANT_ID')
        user_id = req.headers.get('X_USER_ID')
        self.log.info('_sanitize_shared_nets - '
                      'Started sanitizing shared nets '
                      'tenant_id %s user_id %s' % (tenant_id, user_id))
        headers = req.headers
        response = req.get_response(self.app)
        body = response.json
        self.log.info('_sanitize_shared_nets - '
                      'Shared IP request json body -> ' + str(body))
        networks = body.get('networks')
        whitelist = set(headers.get('X_NETWORK_WHITELIST', '').split(','))
        blacklist = set(headers.get('X_NETWORK_BLACKLIST', '').split(','))

        # Collect the shared network ids
        shared_nets = set(n['id'] for n in networks if n['shared'])
        self.log.info('_sanitize_shared_nets - '
                      'Shared nets %s for tenant_id %s and user_id %s' %
                      (str(shared_nets), tenant_id, user_id))
        # Collect the unshared network ids
        unshared_nets = set(n['id'] for n in networks if not n['shared'])
        self.log.info('_sanitize_shared_nets - '
                      'Unshared nets %s for tenant_id %s and user_id %s' %
                      (str(unshared_nets), tenant_id, user_id))
        # Only allow configured or whitelisted shared networks
        # But definitely remove blacklisted networks
        okay_nets = set(n for n in shared_nets if n in
                        whitelist.union(self.trusted_nets) - blacklist)
        self.log.info('_sanitize_shared_nets - '
                      'Okay nets %s for tenant_id %s and user_id %s' %
                      (str('okay_nets'), tenant_id, user_id))
        # Use the networks that are either ok or unshared
        body['networks'] = [n for n in networks if n['id'] in
                            okay_nets.union(unshared_nets)]
        response.json = body

        return response

    @webob.dec.wsgify
    def __call__(self, req):
        super(TrustedSharedNetwork, self).__call__(req)
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
