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
import logging
import webob.dec
import webob.exc

import wafflehaus.resource_filter as rf


class DefaultIPPolicy(object):

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        logname = __name__
        self.log = logging.getLogger(conf.get('log_name', logname))
        self.log.info('Starting wafflehaus default ip policy middleware')
        self.testing = (conf.get('testing') in
                        (True, 'true', 't', '1', 'on', 'yes', 'y'))
        self.resource = conf.get('resource', 'POST /v2.0/subnets')
        self.resources = rf.parse_resources(self.resource)

    def _add_allocation_pools(self, req):
        pass

    def _modify_allocation_pools(self, req):
        self.log.info("derp")

    def _filter_policy(self, req):
        body = req.body
        try:
            body_json = json.loads(body)
        except ValueError:
            return webob.exc.HTTPBadRequest
        subnets = body_json.get('subnets')
        if subnets is None:
            return self.app
        for subnet in subnets:
            alloc_pools = subnet.get('allocation_pools')
            if alloc_pools is None:
                self._add_allocation_pools(req)
            else:
                self._modify_allocation_pools(req)
        self.body = body
        return self.app

    @webob.dec.wsgify
    def __call__(self, req):
        if not rf.matched_request(req, self.resources):
            return self.app
        return self._filter_policy(req)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def block_resource(app):
        return DefaultIPPolicy(app, conf)
    return block_resource
