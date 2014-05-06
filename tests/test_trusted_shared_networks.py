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
import uuid
from tests import test_base
import webob.dec
import webob.response

from wafflehaus.neutron.shared_network import trusted


class FakeWebApp(object):
    def __init__(self, response=None):
        self.response = response
        self.body = response.body

    @webob.dec.wsgify
    def __call__(self, req):
        return self.response


class TestTrustedSharedNetworksFilter(test_base.TestBase):

    def setUp(self):
        self.trusted_id1 = "0000"
        self.trusted_id2 = "1111"
        self.untrusted_id1 = "2222"
        self.untrusted_id2 = "3333"

        self.app = FakeWebApp(response=self.create_response(0, 1, 0, 0))

        self.trusted_conf = {"trusted": [self.trusted_id1]}
        self.trusted_confs = {"trusted": [self.trusted_id1, self.trusted_id2]}

        self.default_mock = mock.Mock()

        self.headers_whitelist1 = {'X_NETWORK_WHITELIST': self.untrusted_id1}
        whitelist = [self.untrusted_id1, self.untrusted_id2]
        self.headers_whitelist2 = {'X_NETWORK_WHITELIST': ','.join(whitelist)}

        self.headers_blacklist1 = {'X_NETWORK_BLACKLIST': self.trusted_id1}
        blacklist = [self.trusted_id1, self.trusted_id2]
        self.headers_blacklist2 = {'X_NETWORK_BLACKLIST': ','.join(blacklist)}

        self.headers_mixed = {'X_NETWORK_BLACKLIST': self.trusted_id2,
                              'X_NETWORK_WHITELIST': self.untrusted_id1}

    def _create_trusted_network(self, trusted_id):
        return '{"subnets": [], "status": "ACTIVE", "name": "derp", '\
            '"id": "%s", "shared": true, "tenant_id": "provider"}' % trusted_id

    def _create_tenant_network(self, shared=False):
        id = str(uuid.uuid4())
        return '{"subnets": [], "status": "ACTIVE", "name": "derp", '\
            '"id": "%s", "shared": %s, "tenant_id": "user"}' % (
                id, ("true" if shared else "false"))

    def _create_network(self, shared=False, id=None):
        id = id if id is not None else str(uuid.uuid4())
        return '{"subnets": [], "status": "ACTIVE", "name": "derp", '\
            '"id": "%s", "shared": %s}' % (id, ("true" if shared else "false"))

    def _create_network_list(self, shared, not_shared, trusted, tenant):
        nets = []
        for i in range(0, not_shared):
            nets.append(self._create_network())

        if shared >= 2:
            nets.append(self._create_network(shared=True,
                                             id=self.untrusted_id2))
        if shared >= 1:
            nets.append(self._create_network(shared=True,
                                             id=self.untrusted_id1))

        if trusted >= 2:
            nets.append(self._create_trusted_network(self.trusted_id2))
        if trusted >= 1:
            nets.append(self._create_trusted_network(self.trusted_id1))
        if tenant > 0:
            nets.append(self._create_tenant_network(shared=True))
        return '{"networks": [%s]}' % ','.join(nets)

    def create_response(self, shared, not_shared, trusted, tenant):
        body = self._create_network_list(shared, not_shared, trusted, tenant)
        res = webob.response.Response(body=body)
        return res

    def _compare_net_list(self, a, b):
        for net_a in a:
            found = False
            for net_b in b:
                if net_a.get('id') == net_b.get('id'):
                    found = True
            if not found:
                return False
        return True

    def _net_lists_equal(self, a, b):
        a = json.loads(a).get("networks")
        b = json.loads(b).get("networks")
        return self._compare_net_list(a, b) and self._compare_net_list(b, a)

    def test_default_intance_create(self):
        self.app = FakeWebApp(response=self.create_response(0, 1, 0, 0))
        result = trusted.filter_factory({})(self.app)
        self.assertIsNotNone(result)

    def test_do_not_modify_response_no_shared_nets(self):
        app = FakeWebApp(response=self.create_response(0, 1, 0, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(1, len(app_networks))
        self.assertFalse(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory({})(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET')

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertTrue(self._net_lists_equal(app.body, resp.body))
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(1, len(body_networks))
        self.assertFalse(any(n.get('shared') for n in body_networks))

    def test_do_not_modify_response_with_trusted_nets(self):
        app = FakeWebApp(response=self.create_response(0, 1, 1, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(2, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_conf)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET')

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(2, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))

    def test_do_not_modify_response_with_multiple_trusted_nets(self):
        app = FakeWebApp(response=self.create_response(0, 1, 2, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(3, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_confs)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET')

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(3, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))

    def test_do_not_modify_response_with_only_trusted_nets(self):
        app = FakeWebApp(response=self.create_response(0, 0, 2, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(2, len(app_networks))
        self.assertTrue(all(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_confs)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET')

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(2, len(body_networks))
        self.assertTrue(all(n.get('shared') for n in body_networks))

    def test_do_modify_response_with_mixed_nets(self):
        app = FakeWebApp(response=self.create_response(1, 1, 2, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(4, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_confs)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET')

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(3, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))

    def test_do_modify_response_with_shared_nets(self):
        app = FakeWebApp(response=self.create_response(1, 1, 0, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(2, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory({})(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET')

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(1, len(body_networks))
        self.assertFalse(any(n.get('shared') for n in body_networks))

    def test_do_not_modify_response_with_shared_nets_whitelisted(self):
        app = FakeWebApp(response=self.create_response(1, 1, 0, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(2, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory({})(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET',
                                       headers=self.headers_whitelist1)

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(2, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))

    def test_do_not_modify_response_with_shared_nets_whitelisted_mixed(self):
        app = FakeWebApp(response=self.create_response(1, 1, 1, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(3, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_conf)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET',
                                       headers=self.headers_whitelist1)

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(3, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))

    def test_do_not_modify_response_with_shared_nets_whitelisted_mixed2(self):
        app = FakeWebApp(response=self.create_response(1, 0, 1, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(2, len(app_networks))
        self.assertTrue(all(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_conf)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET',
                                       headers=self.headers_whitelist1)

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(2, len(body_networks))
        self.assertTrue(all(n.get('shared') for n in body_networks))

    def test_override_trusted_conf_with_blacklist(self):
        app = FakeWebApp(response=self.create_response(0, 1, 2, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(3, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_confs)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET',
                                       headers=self.headers_blacklist1)

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(2, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))
        self.assertFalse(any(n.get('id') == self.trusted_id1
                         for n in body_networks))
        self.assertTrue(any(n.get('id') == self.trusted_id2
                        for n in body_networks))

    def test_override_trusted_conf_with_blacklist_multiples(self):
        app = FakeWebApp(response=self.create_response(0, 2, 2, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(4, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_confs)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET',
                                       headers=self.headers_blacklist2)

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(2, len(body_networks))
        self.assertFalse(any(n.get('shared') for n in body_networks))
        self.assertFalse(any(n.get('id') == self.trusted_id1
                         for n in body_networks))
        self.assertFalse(any(n.get('id') == self.trusted_id2
                         for n in body_networks))

    def test_all_the_things(self):
        app = FakeWebApp(response=self.create_response(2, 2, 2, 0))
        app_networks = json.loads(app.body).get("networks")
        self.assertEqual(6, len(app_networks))
        self.assertTrue(any(n.get('shared') for n in app_networks))

        result = trusted.filter_factory(self.trusted_confs)(app)
        resp = result.__call__.request('/v2.0/networks?shared=true',
                                       method='GET',
                                       headers=self.headers_mixed)

        self.assertTrue(isinstance(resp, webob.response.Response))
        self.assertNotEqual(app.body, resp.body)
        body_networks = json.loads(resp.body).get("networks")
        self.assertEqual(4, len(body_networks))
        self.assertTrue(any(n.get('shared') for n in body_networks))
        self.assertTrue(any(n.get('id') == self.trusted_id1
                        for n in body_networks))
        self.assertFalse(any(n.get('id') == self.trusted_id2
                         for n in body_networks))
        self.assertTrue(any(n.get('id') == self.untrusted_id1
                        for n in body_networks))
        self.assertFalse(any(n.get('id') == self.untrusted_id2
                         for n in body_networks))

    def test_do_nothing_when_testing(self):
        result = trusted.filter_factory({'testing': 'true'})(self.app)
        pkg = 'wafflehaus.neutron.shared_network.trusted.TrustedSharedNetwork'
        with patch(pkg + '._sanitize_shared_nets', self.default_mock) as mock:
            result.__call__.request('/v2.0/networks?shared=true', method='GET')
            self.assertFalse(mock.called)
            result.__call__.request('/v2.0/networks.json?shared=true',
                                    method='GET')
            self.assertFalse(mock.called)
            result.__call__.request('/v2.0/networks.xml?shared=true',
                                    method='GET')
            self.assertFalse(mock.called)

    def test_do_call_on_correct_request(self):
        result = trusted.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.shared_network.trusted.TrustedSharedNetwork'
        with patch(pkg + '._sanitize_shared_nets', self.default_mock) as mock:
            result.__call__.request('/v2.0/networks?shared=true', method='GET')
            self.assertTrue(mock.called)
            result.__call__.request('/v2.0/networks.json?shared=true',
                                    method='GET')
            self.assertTrue(mock.called)
            result.__call__.request('/v2.0/networks.xml?shared=true',
                                    method='GET')
            self.assertTrue(mock.called)

    def test_do_not_filter_on_other_requests(self):
        result = trusted.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.shared_network.trusted.TrustedSharedNetwork'
        with patch(pkg + '._shared_nets_filter', self.default_mock) as mock:
            resp = result.__call__.request('/v2.0/networks', method='POST')
            self.assertFalse(mock.called)
            resp = result.__call__.request('/v2.0/networks', method='PUT')
            self.assertFalse(mock.called)
            resp = result.__call__.request('/v2.0/networks', method='DELETE')
            self.assertFalse(mock.called)
            resp = result.__call__.request('/v2.0/subnets', method='GET')
            self.assertFalse(mock.called)
        self.assertEqual(resp, self.app)

    def test_do_not_filter_unshared_requests(self):
        result = trusted.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.shared_network.trusted.TrustedSharedNetwork'
        with patch(pkg + '._sanitize_shared_nets', self.default_mock) as mock:
            resp = result.__call__.request('/v2.0/networks', method='GET')
            self.assertFalse(mock.called)
        self.assertEqual(resp, self.app)
