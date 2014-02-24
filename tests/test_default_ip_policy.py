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
import contextlib
import mock
from mock import patch
from tests import test_base

from wafflehaus.neutron.ip_policy import create_default


class TestDefaultIPPolicy(test_base.TestBase):
    def setUp(self):
        self.app = mock.Mock()

        self.add_mock = mock.Mock()
        self.mod_mock = mock.Mock()

        self.v4_body = ('{ "subnets":[' +
                        '{' +
                        '"cidr":"192.168.199.0/24",' +
                        '"ip_version":4,' +
                        '"network_id":"some_id"' +
                        '}' +
                        '] }')

        self.v4_has_body = ('{ "subnets":[' +
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

    def test_default_instance_create(self):
        result = create_default.filter_factory({})(self.app)
        self.assertIsNotNone(result)
        resp = result.__call__.request('/', method='GET')
        self.assertEqual(resp, self.app)

    def test_matched_configured(self):
        conf = {'resource': 'POST /derp'}
        result = create_default.filter_factory(conf)(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.add_mock) as mock:
            result.__call__.request('/derp', method='POST')
            self.assertTrue(mock.called)

    def test_matched_default(self):
        result = create_default.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.add_mock) as mock:
            result.__call__.request('/v2.0/subnets', method='POST')
            self.assertTrue(mock.called)

    def test_not_matched_default(self):
        result = create_default.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.add_mock) as mock:
            result.__call__.request('/v2.0/subnets', method='GET')
            self.assertFalse(mock.called)

    def test_not_matched(self):
        result = create_default.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with patch(pkg + '._filter_policy', self.add_mock) as mock:
            result.__call__.request('/testing', method='POST')
            self.assertFalse(mock.called)

    @contextlib.contextmanager
    def test_add_called(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v4_body
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with contextlib.nested(
            mock.patch(pkg + '._add_allocation_pools'),
            mock.patch(pkg + '._modify_allocation_pools')
        ) as (add, mod):
            result.__call__.request('/v2.0/subnets', method='POST',
                                    body=body)
            self.assertTrue(add.called)
            self.assertFalse(mod.called)

    @contextlib.contextmanager
    def test_mod_called(self):
        result = create_default.filter_factory({})(self.app)
        body = self.v4_has_body
        pkg = 'wafflehaus.neutron.ip_policy.create_default.DefaultIPPolicy'
        with contextlib.nested(
            mock.patch(pkg + '._add_allocation_pools'),
            mock.patch(pkg + '._modify_allocation_pools')
        ) as (add, mod):
            result.__call__.request('/v2.0/subnets', method='POST',
                                    body=body)
            self.assertFalse(add.called)
            self.assertTrue(mod.called)

    def test_body_modified(self):
        self.skipTest("Just for now")
        result = create_default.filter_factory({})(self.app)
        body = self.v4_body
        resp = result.__call__.request('/v2.0/subnets', method='POST',
                                       body=body)
        self.assertTrue(200, resp.status_code)
        self.assertNotEqual(result.body, body)
