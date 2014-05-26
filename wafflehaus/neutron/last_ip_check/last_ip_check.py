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
import netaddr
import webob.dec
import webob.exc

from wafflehaus.base import WafflehausBase


class LastIpCheck(WafflehausBase):
    def __init__(self, app, conf):
        super(LastIpCheck, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)
        self.log.info('Starting wafflehaus last_ip_check middleware')

    def _check_basics(self, req):
        if req.content_length == 0:
            return False
        method = req.method
        if method not in ['PUT']:
            return False
        url = req.path
        url_parts = url.split('/')
        if 'ports' not in url and 'ports' not in url_parts[len(url_parts) - 2]:
            return False
        return True

    def _should_run(self, req):
        basic_check = self._check_basics(req)
        if isinstance(basic_check, webob.exc.HTTPException) or not basic_check:
            return basic_check
        body = req.body
        try:
            body_json = json.loads(body)
        except ValueError:
            return webob.exc.HTTPBadRequest
        port_info = body_json.get('port')
        if port_info is None:
            return False
        fixed_ips = port_info.get('fixed_ips')
        if fixed_ips is None:
            return False
        self.fixed_ips = fixed_ips
        return True

    def _is_last_ip(self, req):
        if not hasattr(self, 'fixed_ips') or self.fixed_ips is None:
            return self.app
        if len(self.fixed_ips) == 0:
            return webob.exc.HTTPForbidden()
        for fixed_ip in self.fixed_ips:
            ip_str = fixed_ip.get('ip_address')
            ip = netaddr.IPAddress(ip_str)
            if ip.version == 4:
                """If there is an ipv4 there, we're good"""
                return self.app
        self.log.error('Attempting to remove last ipv4')
        return webob.exc.HTTPForbidden()

    @webob.dec.wsgify
    def __call__(self, req):
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
