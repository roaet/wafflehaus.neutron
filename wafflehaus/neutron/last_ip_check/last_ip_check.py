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
import webob.exc

from wafflehaus.base import WafflehausBase


class LastIpCheck(WafflehausBase):
    def __init__(self, app, conf):
        super(LastIpCheck, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)

    def _check_basics(self, req):
        context_dict = req.environ.get('neutron.context')
        if context_dict:
            self.log.info('_check_basics - Neutron Context ' +
                          'request id %s, project id %s, '
                          'tenant name %s, is admin %s, user id %s'
                          % (str(context_dict.request_id),
                             str(context_dict.project_id),
                             str(context_dict.tenant_name),
                             str(context_dict.is_admin),
                             str(context_dict.user_id)))
        tenant_id = req.headers.get('X_TENANT_ID')
        user_id = req.headers.get('X_USER_ID')
        self.log.info('_check_basics - '
                      'tenant_id %s and user_id '
                      '%s' % (tenant_id, user_id))
        if req.content_length == 0:
            self.log.debug('_check_basics - '
                           'Content length of request is zero '
                           '_check_basics returned False for module '
                           'tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return False
        method = req.method
        if method not in ['PUT']:
            self.log.debug('_check_basics - PUT not in request method '
                           'tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return False
        url = req.path
        url_parts = url.split('/')
        if 'ports' not in url and 'ports' not in url_parts[len(url_parts) - 2]:
            self.log.debug('_check_basics - Port '
                           'not found in url, or url_parts[len('
                           'url_parts) _check_basics retuned False '
                           'tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return False
        return True

    def _should_run(self, req):
        tenant_id = req.headers.get('X_TENANT_ID')
        user_id = req.headers.get('X_USER_ID')
        basic_check = self._check_basics(req)
        if isinstance(basic_check, webob.exc.HTTPException) or not basic_check:
            return basic_check
        body = req.body
        try:
            body_json = json.loads(body)
        except ValueError:
            self.log.error('_should_run - Failed while loading json, '
                           'check for invalid json tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return webob.exc.HTTPBadRequest
        try:
            port_info = body_json.get('port')
        except AttributeError:
            self.log.error('_should_run - Port not found in '
                           'request body json tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return False
        if port_info is None:
            self.log.debug('_should_run - Port info is None '
                           'in the request body json tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return False
        fixed_ips = port_info.get('fixed_ips')
        if fixed_ips is None:
            self.log.debug('_should_run - Fixed IP is None '
                           'in request body json tenant_id %s and user_id '
                           '%s' % (tenant_id, user_id))
            return False
        self.fixed_ips = fixed_ips
        return True

    def _is_last_ip(self, req):
        tenant_id = req.headers.get('X_TENANT_ID')
        user_id = req.headers.get('X_USER_ID')
        self.log.info('_is_last_ip - Checking if the attached IP is '
                      'the last address tenant_id %s and user_id %s' %
                      (tenant_id, user_id))
        if not hasattr(self, 'fixed_ips') or self.fixed_ips is None:
            return self.app
        if len(self.fixed_ips) == 0:
            self.log.error('_is_last_ip - PUT requests to remove all '
                           'IPs from a Port are not allowed tenant_id %s '
                           'and user_id %s' % (tenant_id, user_id))
            return webob.exc.HTTPForbidden("fixed_ips cannot be empty")
        else:
            return self.app
        return webob.exc.HTTPForbidden()

    @webob.dec.wsgify
    def __call__(self, req):
        super(LastIpCheck, self).__call__(req)
        if not self.enabled:
            return self.app

        res = self._should_run(req)
        if isinstance(res, webob.exc.HTTPException):
            return res
        if not res:
            return self.app
        return self._is_last_ip(req)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def check_last_ip(app):
        return LastIpCheck(app, conf)
    return check_last_ip
