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


class APIAdaptor(WafflehausBase):

    def __init__(self, app, conf):
        super(APIAdaptor, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)
        self.log.info('Starting wafflehaus trusted shared nets middleware')

        res = ['POST /v2.0/allocate_for_instance',
               'GET /v2.0/get_instance_nw_info']
        self.resources = rf.parse_resources(','.join(res))

    def _allocate_for_instance(self, req):
        new_req = req.copy()
        resp = new_req.get_response(self.app)
        return resp.body

    def _get_instance_nw_info(self, req):
        pass

    def _execute_request(self, req):
        if 'allocate_for_instance' in req.path:
            return self._allocate_for_instance(req)
        if 'get_instance_nw_info' in req.path:
            return self._get_instance_nw_info(req)
        return self.app

    @webob.dec.wsgify
    def __call__(self, req):
        if not self.enabled:
            return self.app
        if not rf.matched_request(req, self.resources):
            return self.app
        return self._execute_request(req)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def api_adaptor(app):
        return APIAdaptor(app, conf)
    return api_adaptor
