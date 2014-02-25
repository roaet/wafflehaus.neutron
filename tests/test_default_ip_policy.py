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
import mock
from mock import patch
from tests import test_base

from wafflehaus.neutron.ip_policy import create_default

class DefaultPolicyTestBase(test_base.TestBase):
    def setUp(self):
        self.app = mock.Mock()

        self.default_mock = mock.Mock()
        self.mod_mock = mock.Mock()

    def _get_allocation_pools_from_body(self, body):
        body_json = json.loads(body)
        print(body_json)
        allocation_pools = body_json["subnets"][0]["allocation_pools"]
        return allocation_pools
    
    def test_default_instance_create(self):
        result = create_default.filter_factory({})(self.app)
        self.assertIsNotNone(result)
        resp = result.__call__.request('/', method='GET')
        self.assertEqual(resp, self.app)

    def test_matched_configured(self):
        conf = {'resource': 'POST /derp'}
        result = create_default.filter_factory(conf)(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.default_mock) as mock:
            result.__call__.request('/derp', method='POST')
            self.assertTrue(mock.called)

    def test_matched_default(self):
        result = create_default.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.default_mock) as mock:
            result.__call__.request('/v2.0/subnets', method='POST')
            self.assertTrue(mock.called)

    def test_not_matched_default(self):
        result = create_default.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.default_mock) as mock:
            result.__call__.request('/v2.0/subnets', method='GET')
            self.assertFalse(mock.called)

    def test_not_matched(self):
        result = create_default.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.default_mock) as mock:
            result.__call__.request('/testing', method='POST')
            self.assertFalse(mock.called)

class TestDefaultIPV4Policy(DefaultPolicyTestBase):
    def setUp(self):
        super(TestDefaultIPV4Policy, self).setUp()

        self.v4_no_alloc = ('{ "subnets":[' +
                            '{' +
                            '"cidr":"192.168.199.0/24",' +
                            '"ip_version":4,' +
                            '"network_id":"some_id"' +
                            '}' +
                            '] }')

        self.v4_has_alloc_same_as_default = ('{ "subnets":[' +
                            '{' +
                            '"cidr":"192.168.199.0/24",' +
                            '"ip_version":4,' +
                            '"network_id":"some_id",' +
                            '"allocation_pools":[' +
                            '{ "end":"192.168.199.254", ' +
                            '"start":"192.168.199.5" }' +
                            ']' +
                            '}' +
                            '] }')
        
        self.v4_has_alloc_bigger_than_default = ('{ "subnets":[' +
                            '{' +
                            '"cidr":"192.168.199.0/24",' +
                            '"ip_version":4,' +
                            '"network_id":"some_id",' +
                            '"allocation_pools":[' +
                            '{ "end":"192.168.199.255", ' +
                            '"start":"192.168.199.0" }' +
                            ']' +
                            '}' +
                            '] }')
        
        self.v4_has_alloc_smaller_than_default = ('{ "subnets":[' +
                            '{' +
                            '"cidr":"192.168.199.0/24",' +
                            '"ip_version":4,' +
                            '"network_id":"some_id",' +
                            '"allocation_pools":[' +
                            '{ "end":"192.168.199.100", ' +
                            '"start":"192.168.199.85" }' +
                            ']' +
                            '}' +
                            '] }')


    def test_body_contains_no_allocation_pools(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v4_no_alloc
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools= self._get_allocation_pools_from_body(result.body)
        self.assertEqual("192.168.199.5", allocation_pools[0]["start"])
        self.assertEqual("192.168.199.254", allocation_pools[0]["end"])
    
    def test_body_contains_allocation_pools_same_as_default(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v4_has_alloc_same_as_default
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("192.168.199.5", allocation_pools[0]["start"])
        self.assertEqual("192.168.199.254", allocation_pools[0]["end"])
    
    def test_body_contains_allocation_pool_bigger_than_default(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v4_has_alloc_bigger_than_default
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("192.168.199.5", allocation_pools[0]["start"])
        self.assertEqual("192.168.199.254", allocation_pools[0]["end"])

    def test_body_contains_allocation_pool_smaller_than_default(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v4_has_alloc_smaller_than_default
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("192.168.199.85", allocation_pools[0]["start"])
        self.assertEqual("192.168.199.100", allocation_pools[0]["end"])


class TestDefaultIPV6Policy(DefaultPolicyTestBase):
    def setUp(self):
        super(TestDefaultIPV6Policy, self).setUp()

        self.v6_no_alloc = ('{ "subnets":[' +
                            '{' +
                            '"cidr":"2607:f0d0:1002:51::0/96",' +
                            '"ip_version":6,' +
                            '"network_id":"some_id"' +
                            '}' +
                            '] }')

        self.v6_has_alloc_same_as_default = ('{ "subnets":[' +
                       '{' +
                       '"cidr":"2607:f0d0:1002:51::0/96",' +
                       '"ip_version":6,' +
                       '"network_id":"some_id",' +
                       '"allocation_pools":[' +
                       '{ "end":"2607:f0d0:1002:51::ffff:fffe", ' +
                       '"start":"2607:f0d0:1002:51::a" }' +
                       ']' +
                       '}' +
                       '] }')
        
        self.v6_has_alloc_bigger_than_default = ('{ "subnets":[' +
                       '{' +
                       '"cidr":"2607:f0d0:1002:51::0/96",' +
                       '"ip_version":6,' +
                       '"network_id":"some_id",' +
                       '"allocation_pools":[' +
                       '{ "end":"2607:f0d0:1002:51::ffff:ffff", ' +
                       '"start":"2607:f0d0:1002:51::" }' +
                       ']' +
                       '}' +
                       '] }')
        
        self.v6_has_alloc_smaller_than_default = ('{ "subnets":[' +
                            '{' +
                            '"cidr":"2607:f0d0:1002:51::0/96",' +
                            '"ip_version":6,' +
                            '"network_id":"some_id",' +
                            '"allocation_pools":[' +
                            '{ "end":"2607:f0d0:1002:51::64", ' +
                            '"start":"2607:f0d0:1002:51::56" }' +
                            ']' +
                            '}' +
                            '] }')

    def test_body_contains_no_allocation_pools(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v6_no_alloc
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("2607:f0d0:1002:51::a", allocation_pools[0]["start"])
        self.assertEqual("2607:f0d0:1002:51::ffff:fffe",
                         allocation_pools[0]["end"])
    
    def test_body_contains_allocation_pools_same_as_default(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v6_has_alloc_same_as_default
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("2607:f0d0:1002:51::a", allocation_pools[0]["start"])
        self.assertEqual("2607:f0d0:1002:51::ffff:fffe",
                         allocation_pools[0]["end"])
    
    def test_body_contains_allocation_pool_bigger_than_default(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v6_has_alloc_bigger_than_default
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("2607:f0d0:1002:51::a", allocation_pools[0]["start"])
        self.assertEqual("2607:f0d0:1002:51::ffff:fffe",
                         allocation_pools[0]["end"])

    def test_body_contains_allocation_pool_smaller_than_default(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v6_has_alloc_smaller_than_default
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
        allocation_pools = self._get_allocation_pools_from_body(result.body)
        self.assertEqual("2607:f0d0:1002:51::56", allocation_pools[0]["start"])
        self.assertEqual("2607:f0d0:1002:51::64",
                         allocation_pools[0]["end"])
