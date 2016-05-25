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
from oslo_config import cfg
from wafflehaus.try_context import context_filter
import webob.exc
from tests import test_base


class TestNeutronContext(test_base.TestBase):
    def setUp(self):
        super(TestNeutronContext, self).setUp()
        find_policy_file_patch = mock.patch(
            "oslo_config.cfg.find_config_files")
        from neutron import policy

        adv_svc_patch = mock.patch(
            "neutron.policy.check_is_advsvc")
        policy._rules = {}
        find_policy_file_patch.start()
        self.adv_svc = adv_svc_patch.start()
        self.adv_svc.return_value = False

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
        result.__call__.request('/', method='HEAD', headers=headers)

    def test_create_strategy_neutron_no_user(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json', }
        resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)

    def test_create_strategy_neutron_with_no_roles(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': None, }
        resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)

    def test_create_strategy_neutron_with_empty_roles(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': '', }
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
        resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)
        self.assertTrue('testrole2' in context.roles)
        self.assertEqual(2, len(context.roles))

    def test_requires_auth_will_fail_without_info(self):
        result = context_filter.filter_factory(self.strat_neutron_a)(self.app)
        self.assertIsNotNone(result)
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json',
                   'X_ROLES': 'testrole, testrole2', }
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
        resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        self.assertEqual(1, policy_check.call_count)
        context = result.strat_instance.context
        self.assertTrue(hasattr(context, 'roles'))
        self.assertTrue('testrole' in context.roles)
        self.assertTrue('testrole2' in context.roles)
        self.assertFalse(context.is_admin)
        self.assertEqual(2, len(context.roles))

    def test_advsvc_is_false_when_admin_and_not_advsvc_role(self):
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json'}
        resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertFalse(context.is_advsvc)

    def test_advsvc_is_true_when_policy_says_it_is(self):
        self.adv_svc.return_value = True
        result = context_filter.filter_factory(self.strat_neutron)(self.app)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, context_filter.ContextFilter))
        self.assertFalse('neutron.context' in self.req)
        headers = {'Content-Type': 'application/json'}
        resp = result.__call__.request('/', method='HEAD', headers=headers)
        self.assertEqual(self.app, resp)
        context = result.strat_instance.context
        self.assertTrue(context.is_advsvc)
