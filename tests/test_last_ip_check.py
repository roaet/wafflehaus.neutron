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
from tests import test_base
from mock import patch

from wafflehaus.neutron.last_ip_check import last_ip_check


class TestLastIpCheck(test_base.TestBase):
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
        self.global_conf = {}
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
        env = {
            'PATH_INFO': '/port/12345',
        }
        self.checker(env, self.start_response)
        self.assertEqual(self.start_response.call_count, 1)

    def test_call_incorrect_route(self):
        env = {
            'PATH_INFO': '/test',
            'REQUEST_METHOD': 'PUT',
        }
        self.assertEqual(self.return_value,
                         self.checker(env, self.start_response))
        self.assertEqual(self.start_response.call_count, 0)

    def _create_env(self, method, body):
        fake_file = mock.Mock()
        fake_file.read = mock.Mock()
        fake_file.read.return_value = body
        env = {
            'PATH_INFO': '/ports/12345',
            'REQUEST_METHOD': 'PUT',
            'wsgi.input': fake_file,
            'CONTENT_LENGTH': len(body),
        }
        return env

    def test_call_no_body(self):
        env = self._create_env('PUT', '')
        with patch.object(last_ip_check.LastIpCheck, '_is_last_ip',
                          return_value=None) as mock_method:
            self.assertEqual(self.return_value,
                             self.checker(env, self.start_response))
            self.assertEqual(self.start_response.call_count, 0)
            self.assertEqual(mock_method.call_count, 0)

    def test_call_no_fixed_ips(self):
        env = self._create_env('PUT', self.bad_no_fixed)
        with patch.object(last_ip_check.LastIpCheck, '_is_last_ip',
                          return_value=None) as mock_method:
            self.assertEqual(self.return_value,
                             self.checker(env, self.start_response))
            self.assertEqual(self.start_response.call_count, 0)
            self.assertEqual(mock_method.call_count, 0)

    def test_call_not_ports(self):
        env = self._create_env('PUT', self.bad_resource)
        with patch.object(last_ip_check.LastIpCheck, '_is_last_ip',
                          return_value=None) as mock_method:
            self.assertEqual(self.return_value,
                             self.checker(env, self.start_response))
            self.assertEqual(self.start_response.call_count, 0)
            self.assertEqual(mock_method.call_count, 0)

    def test_call_correct_body(self):
        env = self._create_env('PUT', self.good_empty)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 1)

    def test_only_v6(self):
        """This situation occurs if any ip was removed and ipv6 is left."""
        env = self._create_env('PUT', self.good_only_v6)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 1)

    def test_add_v4(self):
        """This situation occurs when a user is adding an ipv4 to an empty
        list.
        """
        env = self._create_env('PUT', self.good_add_v4)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 0)

    def test_add_v6(self):
        """This situation occurs when a user is adding an ipv6 to an empty
        list.
        """
        env = self._create_env('PUT', self.good_add_v6)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 1)

    def test_add_v6_w4(self):
        """This situation occurs when a user is adding an ipv6 to a list of
        other ipv4s.
        """
        env = self._create_env('PUT', self.good_add_v6_w4)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 0)

    def test_add_v4_w4(self):
        """This situation occurs when a user is adding an ipv4 to a list of
        other ipv4s.
        """
        env = self._create_env('PUT', self.good_add_v4_w4)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 0)

    def test_add_v4_w6(self):
        """This situation occurs when a user is adding an ipv4 to a list of
        other ipv6s.
        """
        env = self._create_env('PUT', self.good_add_v4_w6)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 0)

    def test_add_v6_w6(self):
        """This situation occurs when a user is adding an ipv6 to a list of
        other ipv6s.
        """
        env = self._create_env('PUT', self.good_add_v6_w6)
        self.checker(env, self.start_response)
        self.assertEquals(self.start_response.call_count, 1)
