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
import netaddr
import webob.dec
import webob.exc


def response_headers(content_length):
    """Creates the default headers for all errors."""
    return [
        ('Content-type', 'text/html'),
        ('Content-length', str(content_length)),
    ]


def do_500(start_response):
    """Performs a standard 500 error"""
    start_response("500 Internal Server Error",
                   response_headers(0))
    return ["", ]


def do_403(start_response):
    msg = "400 Forbidden. Cannot remove last v4 address from interface"
    start_response(msg, response_headers(0))
    return ["", ]


class Error403(Exception):
    pass


class Error500(Exception):
    pass


class LastIpCheck(object):
    def __init__(self, app, conf):
        self.conf = conf
        self.app = app
        self.log = logging.getLogger(conf.get('log_name', __name__))
        self.log.info('Starting wafflehaus last_ip_check middleware')

    def _prep_url(self, url):
        if url is None:
            self.log.error('Url info is empty')
        url_parts = url.split('/')
        if len(url_parts) < 3:
            return False
        self.resource = url_parts[1]
        self.port = url_parts[2]
        return True

    def _check_basics(self, req):
        if req.content_length == 0:
            return False

        method = req.method
        if(not self._prep_url(req.path) or
                method not in ['PUT', 'DELETE'] or
                self.resource != 'ports'):
            return False
        return True

    def _should_run(self, req):
        basic_check = self._check_basics(req)
        if isinstance(basic_check, webob.exc.HTTPException) or not basic_check:
            self.log.info("Failed basic checks with: " + str(basic_check))
            return basic_check
        body = req.body
        try:
            body_json = json.loads(body)
        except ValueError:
            return webob.exc.HTTPBadRequest
        self.log.info(str(body_json))
        port_info = body_json.get('port')
        if port_info is None:
            return False
        fixed_ips = port_info.get('fixed_ips')
        if fixed_ips is None:
            return False
        self.fixed_ips = fixed_ips
        return True

    def _is_last_ip(self, req):
        if len(self.fixed_ips) == 0:
            return webob.exc.HTTPForbidden()
        for fixed_ip in self.fixed_ips:
            if 'ip_address' not in fixed_ip:
                #TODO(jlh): need to add the DB connection to do this
                subnet_id = fixed_ip.get('subnet_id')
                if subnet_id == "ipv4":
                    """If adding to ipv4 subnet, we're good"""
                    return self.app
            else:
                ip_str = fixed_ip.get('ip_address')
                ip = netaddr.IPAddress(ip_str)
                if ip.version == 4:
                    """If there is an ipv4 there, we're good"""
                    return self.app
        return webob.exc.HTTPForbidden()

    @webob.dec.wsgify
    def __call__(self, req):
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
