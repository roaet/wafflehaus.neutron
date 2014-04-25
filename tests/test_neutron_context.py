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
import mock
from mock import patch
from wafflehaus.try_context import context_filter
from tests import test_base


class TestNeutronContext(test_base.TestBase):
    def setUp(self):
        super(TestNeutronContext, self).setUp()
        self.app = mock.Mock()
        self.app.return_value = "OK"
        self.start_response = mock.Mock()
        self.test_cls = "tests.test_try_context.TestContextClass"
        self.neutron_cls = "wafflehaus.neutron.context.%s.%s" % (
            "neutron_context", "NeutronContextFilter")

        self.req = {'REQUEST_METHOD': 'HEAD',
                    'X_USER_ID': '12345', }

        self.local_conf = {"context_class": self.test_cls,
                           "context_key": "context.test", }

        self.strat_neutron = {"context_strategy": self.neutron_cls}
        self.strat_none = {"context_strategy": "none"}
        self.strat_test = {"context_strategy": "test"}
        self.get_admin_mock = mock.Mock()
        self.get_admin_mock.return_value = ['admin']

    def test_create_strategy_neutron(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_USER_ID': 'derp', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock) as mocked_get:
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        self.assertTrue(mocked_get.called)

    def test_create_strategy_neutron_no_user(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)

    def test_create_strategy_neutron_with_no_roles(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': None, }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)

    def test_create_strategy_neutron_with_empty_roles(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': '', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))

    def test_create_strategy_neutron_with_role(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': 'testrole', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)

    def test_create_strategy_neutron_with_roles(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': 'testrole, testrole2', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)
        self.assertTrue('testrole2' in context.roles)

    def test_create_strategy_neutron_appends_to_admin_role(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': 'testrole, testrole2', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)
        self.assertTrue('testrole2' in context.roles)
        set_a = set(['testrole', 'testrole2'])
        set_b = set(context.roles)
        set_result = set_b - set_a
        self.assertTrue(set_a not in set_result)
