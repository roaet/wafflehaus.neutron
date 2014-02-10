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

    def _prep_url(self, url, start_response):
        if url is None:
            self.log.error('Url info is empty')
            raise Error500()
        url_parts = url.split('/')
        if len(url_parts) < 3:
            return False
        self.resource = url_parts[1]
        self.port = url_parts[2]
        return True

    def _check_basics(self, env, start_response):
        method = env.get('REQUEST_METHOD')
        if method is None:
            self.log.error('Request method is unknown')
            raise Error500()

        if(not self._prep_url(env.get('PATH_INFO'), start_response) or
                method not in ['PUT', 'DELETE'] or
                self.resource != 'ports'):
            return False
        return True

    def _should_run(self, env, start_response):
        if not self._check_basics(env, start_response):
            return False
        body = ''
        try:
            length = int(env.get('CONTENT_LENGTH', '0'))
        except ValueError:
            length = 0
        if length == 0:
            return False
        if length != 0:
            body = env['wsgi.input'].read(length)
        try:
            body_json = json.loads(body)
        except ValueError:
            self.log.error("Cowardly not failing on weird json")
            return False
        port_info = body_json.get('port')
        if port_info is None:
            return False
        fixed_ips = port_info.get('fixed_ips')
        if fixed_ips is None:
            return False
        self.fixed_ips = fixed_ips
        return True

    def _is_last_ip(self, env, start_response):
        if len(self.fixed_ips) == 0:
            raise Error403()
        for fixed_ip in self.fixed_ips:
            if 'ip_address' not in fixed_ip:
                #TODO(jlh): need to add the DB connection to do this
                subnet_id = fixed_ip.get('subnet_id')
                if subnet_id == "ipv4":
                    """If adding to ipv4 subnet, we're good"""
                    return
            else:
                ip_str = fixed_ip.get('ip_address')
                ip = netaddr.IPAddress(ip_str)
                if ip.version == 4:
                    """If there is an ipv4 there, we're good"""
                    return
        raise Error403()

    def __call__(self, env, start_response):
        try:
            if not self._should_run(env, start_response):
                return self.app(env, start_response)
            self._is_last_ip(env, start_response)
            return self.app(env, start_response)
        except Error500:
            return do_500(start_response)
        except Error403:
            return do_403(start_response)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def check_last_ip(app):
        return LastIpCheck(app, conf)
    return check_last_ip
