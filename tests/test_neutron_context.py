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
import webob.exc
from tests import test_base


class TestNeutronContext(test_base.TestBase):
    def setUp(self):
        super(TestNeutronContext, self).setUp()
        find_policy_file_patch = mock.patch(
            "neutron.common.utils.find_config_file")
        read_policy_file_patch = mock.patch(
            "neutron.common.utils.read_cached_file")
        from neutron.openstack.common import policy

        adv_svc = mock.patch(
            "neutron.policy.check_is_advsvc")
        adv_svc.return_value = False
        policy._rules = {}
        find_policy_file_patch.start()
        read_policy_file_patch.start()
        adv_svc.start()
        self.addCleanup(find_policy_file_patch.stop)
        self.addCleanup(read_policy_file_patch.stop)
        self.addCleanup(adv_svc.stop)

        self.app = mock.Mock()
        self.app.return_value = "OK"
        self.start_response = mock.Mock()
        self.test_cls = "tests.test_try_context.TestContextClass"
        self.neutron_cls = "wafflehaus.neutron.context.%s.%s" % (
            "neutron_context", "NeutronContextFilter")

        self.req = {'REQUEST_METHOD': 'HEAD',
                    'X_USER_ID': '12345', }

        self.local_conf = {"context_class": self.test_cls, 'enabled': 'true',
                           "context_key": "context.test", }

        self.strat_neutron = {"context_strategy": self.neutron_cls,
                              'enabled': 'true'}
        self.strat_neutron_a = {"context_strategy": self.neutron_cls,
                                'enabled': 'true',
                                'require_auth_info': 'true'}
        self.strat_none = {"context_strategy": "none",
                           'enabled': 'true'}
        self.strat_test = {"context_strategy": "test",
                           'enabled': 'true'}
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
        self.assertTrue('admin' in context.roles)
        self.assertEqual(3, len(context.roles))

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
        self.assertTrue('admin' in context.roles)
        self.assertEqual(3, len(context.roles))

    def test_requires_auth_will_fail_without_info(self):
        result = context_filter.filter_factory(self.strat_neutron_a)(self.app)
        self.assertIsNotNone(result)
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': 'testrole, testrole2', }
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertTrue(isinstance(resp, webob.exc.HTTPForbidden))

    def test_requires_auth_is_admin(self):
        result = context_filter.filter_factory(self.strat_neutron_a)(self.app)
        self.assertIsNotNone(result)
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_TENANT_ID': '123456',
                   'X_USER_ID': 'foo',
                   'X_ROLES': 'testrole, testrole2', }
        policy_check = self.create_patch('neutron.policy.check_is_admin')
        policy_check.return_value = True
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        self.assertEqual(1, policy_check.call_count)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)
        self.assertTrue('testrole2' in context.roles)
        self.assertTrue(context.is_admin)
        self.assertEqual(2, len(context.roles))

    def test_requires_auth_is_not_admin(self):
        result = context_filter.filter_factory(self.strat_neutron_a)(self.app)
        self.assertIsNotNone(result)
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_TENANT_ID': '123456',
                   'X_USER_ID': 'foo',
                   'X_ROLES': 'testrole, testrole2', }
        policy_check = self.create_patch('neutron.policy.check_is_admin')
        policy_check.return_value = False
        with patch('neutron.policy.get_admin_roles',
                   self.get_admin_mock):
            resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        self.assertEqual(1, policy_check.call_count)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)
        self.assertTrue('testrole2' in context.roles)
        self.assertFalse(context.is_admin)
        self.assertEqual(2, len(context.roles))
