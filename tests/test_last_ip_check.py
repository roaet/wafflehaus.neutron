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
#import mock
#from neutron import wsgi
#from wafflehaus import rolerouter
import mock
from wafflehaus import tests

from wafflehaus.neutron.last_ip_check import last_ip_check


class TestLastIpCheck(tests.TestCase):
    def _create_body(self, fixed_ips, resource='port', sub='fixed_ips'):
        res = '{"%s": {"%s": [%s]}}' % (resource, sub, ','.join(fixed_ips))
        return res

    def _v4(self, subnet="ipv4"):
        res = '{"subnet_id": "%s", "ip_address": "10.13.20.64"}' % subnet
        return res

    def _v6(self, subnet="ipv6"):
        res = ('{"subnet_id": "%s", "ip_address": "2607:f0d0:1002:51::4"}' %
               subnet)
        return res

    def _add_v4(self, subnet="ipv4"):
        res = '{"subnet_id": "%s"}' % subnet
        return res

    def _add_v6(self, subnet="ipv6"):
        res = '{"subnet_id": "%s"}' % subnet
        return res

    def setUp(self):
        super(TestLastIpCheck, self).setUp()
        self.app = mock.Mock()
        self.return_value = 'app'
        self.app.return_value = self.return_value
        self.start_response = mock.Mock()
        self.global_conf = {'enabled': 'true'}
        self.checker = last_ip_check.filter_factory(self.global_conf)(self.app)

        self.good_empty = self._create_body([])
        self.good_only_v6 = self._create_body([self._v6()])
        self.good_add_v4 = self._create_body([self._add_v4()])
        self.good_add_v6 = self._create_body([self._add_v6()])
        self.good_add_v6_w4 = self._create_body([self._v4(), self._add_v6()])
        self.good_add_v4_w4 = self._create_body([self._v4(), self._add_v4()])
        self.good_add_v4_w6 = self._create_body([self._v6(), self._add_v4()])
        self.good_add_v6_w6 = self._create_body([self._v6(), self._add_v6()])

        self.bad_resource = '{"derp": {"fixed_ips":[{"derp": "derp"}]}}'
        self.bad_no_fixed = '{"port": {"derply":[{"derp": "derp"}]}}'

    def test_create_ip_check(self):
        checker = last_ip_check.filter_factory(self.global_conf)(self.app)
        self.assertTrue(checker is not None)
        self.assertTrue(isinstance(checker, last_ip_check.LastIpCheck))
        call_fx = getattr(checker, "__call__", None)
        self.assertIsNotNone(call_fx)
        self.assertTrue(callable(call_fx))
        self.assertTrue(callable(checker))

    def test_call_no_method(self):
        resp = self.checker.__call__.request('/test/1234', body=None)
        self.assertEqual(self.app, resp)

    def test_call_incorrect_route(self):
        resp = self.checker.__call__.request('/test/1234', method='PUT',
                                             body=None)
        self.assertEqual(self.app, resp)

    def test_call_no_body(self):
        resp = self.checker.__call__.request('/ports/1234', method='PUT',
                                             body=None)
        self.assertEqual(self.app, resp)

    def test_call_no_fixed_ips(self):
        resp = self.checker.__call__.request('/ports/1234', method='PUT',
                                             body=self.bad_no_fixed)
        self.assertEqual(self.app, resp)

    def test_call_not_ports(self):
        resp = self.checker.__call__.request('/ports/1234', method='PUT',
                                             body=self.bad_resource)
        self.assertEqual(self.app, resp)

    def test_call_correct_body(self):
        resp = self.checker.__call__.request('/ports/1234', method='PUT',
                                             body=self.good_empty)
        self.assertEqual(403, resp.status_code)

    def test_only_v6(self):
        """This situation occurs if any ip was removed and ipv6 is left."""
        resp = self.checker.__call__.request('/ports/1234', method='PUT',
                                             body=self.good_only_v6)
        self.assertEqual(403, resp.status_code)

    def test_runtime_override(self):
        self.set_reconfigure()
        result = last_ip_check.filter_factory(self.global_conf)(self.app)
        resp = result.__call__.request('/ports/1234', method='PUT',
                                       body=self.good_only_v6)
        self.assertEqual(403, resp.status_code)
        headers = {'X_WAFFLEHAUS_LASTIPCHECK_ENABLED': False}
        resp = result.__call__.request('/ports/1234', method='PUT',
                                       headers=headers,
                                       body=self.good_only_v6)
        self.assertEqual(self.app, resp)
