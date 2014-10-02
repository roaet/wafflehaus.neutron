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

import json
import webob

from tests import test_base
from wafflehaus.neutron import nova_interaction


class TestNovaInteraction(test_base.TestBase):
    def setUp(self):
        super(TestNovaInteraction, self).setUp()
        self.app = self.fake_app
        self.body = {'port':
                     {'mac_address': "AA:BB:CC:DD:EE",
                      'fixed_ips': "ips_fixed",
                      'instance_id': "id_instance",
                      'network_id': "id_network",
                      'id': "random_port_id",
                      'tenant_id': "id_tenant"}}
        self.conf = {"enabled": "true",
                     "nova_url": "https://novathing.com",
                     "nova_port": 123,
                     "nova_verify_ssl": "false",
                     "neutron_url": "https://neutronthing.com",
                     "neutron_port": "456",
                     "neutron_verify_ssl": "false",
                     "resources": "POST /v2/ports,"
                                  "PUT DELETE /v2/ports/{port_id},"
                                  "POST /v2/ipaddresses,"
                                  "PUT DELETE /v2/ip_addresses/"
                                  "{ipaddress_id}"}
        self.nova_response = (200, "It works!")
        self.neutron_response = (200, {'port':
                                 {'mac_address': "AA:BB:CC:DD:EE",
                                  'fixed_ips': "ips_fixed",
                                  'instance_id': "id_instance",
                                  'network_id': "id_network",
                                  'port_id': "random_port_id",
                                  'tenant_id': "id_tenant"}})

    @webob.dec.wsgify
    def fake_app(self, req):
        return webob.Response(body=json.dumps(self.body), status=200)

    def fake_response(self, req, fail=None):
        resp = self.fake_app(req)
        new_body = resp.json
        if fail is None:
            if req.method.upper() == "DELETE":
                new_body['neutron_callback'] = {"port_id": "random_port_id",
                                                "status": "success"}
            new_body['nova_callback'] = {"instance_id": "id_instance",
                                         "status": "success"}
        elif fail == "nova":
            if req.method.upper() == "DELETE":
                new_body['neutron_callback'] = {"port_id": "random_port_id",
                                                "status": "success"}
            new_body['nova_callback'] = {"instance_id": "id_instance",
                                         "status": "error",
                                         "error": "ERROR!"}
        elif fail == "neutron" and req.method.upper() == "DELETE":
            resp = webob.Response()
            resp.status = 500
            resp.body = json.dumps({"neutron_callback":
                                    {"port_id": "random_port_id",
                                     "status": "error",
                                     "error": "ERROR!"}})
            return resp
        resp.body = json.dumps(new_body)
        return resp

    def test_filter_creation(self):
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)

        self.assertIsNotNone(test_filter)
        self.assertIsInstance(test_filter, nova_interaction.NovaInteraction)
        self.assertTrue(callable(test_filter))

    def test_disabled_filter(self):
        conf = {"enabled": "false"}
        test_filter = nova_interaction.filter_factory(conf)(self.app)
        resp = test_filter(webob.Request.blank("/v2/ports", method="POST"))

        self.assertEqual(resp, self.app)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_get_to_ports(self, mock_neutron, mock_nova):
        """This should look exactly like disabled_filter (we ignore GETs)."""
        test_filter = nova_interaction.filter_factory(self.conf)(self.app)
        resp = test_filter(webob.Request.blank("/v2/ports/random_port_id",
                                               method="GET"))

        self.assertFalse(mock_nova.called)
        self.assertFalse(mock_neutron.called)
        self.assertEqual(resp, self.app)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_post_to_ports(self, mock_neutron, mock_nova):
        mock_conn = mock.MagicMock()
        mock_conn.admin_virtual_interfaces.return_value = self.nova_response
        mock_nova.return_value = mock_conn
        req = webob.Request.blank("/v2/ports", method="POST")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req)

        self.assertFalse(mock_neutron.called)
        self.assertTrue(mock_nova.called)
        self.assertTrue(mock_conn.admin_virtual_interfaces.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, fake_resp.status_code)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_post_to_ports_fail_on_nova(self, mock_neutron, mock_nova):
        mock_conn = mock.MagicMock()
        mock_conn.admin_virtual_interfaces.return_value = (503, "ERROR!")
        mock_nova.return_value = mock_conn
        req = webob.Request.blank("/v2/ports", method="POST")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req, fail="nova")

        self.assertFalse(mock_neutron.called)
        self.assertTrue(mock_nova.called)
        self.assertTrue(mock_conn.admin_virtual_interfaces.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, 500)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_put_to_ports(self, mock_neutron, mock_nova):
        """This is identical to the POST call above, except with PUT."""
        mock_conn = mock.MagicMock()
        mock_conn.admin_virtual_interfaces.return_value = self.nova_response
        mock_nova.return_value = mock_conn
        req = webob.Request.blank("/v2/ports/random_port_id", method="PUT")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req)

        self.assertFalse(mock_neutron.called)
        self.assertTrue(mock_nova.called)
        self.assertTrue(mock_conn.admin_virtual_interfaces.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, fake_resp.status_code)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_put_to_ports_fail_on_nova(self, mock_neutron, mock_nova):
        """This is identical to the POST nova failure above, except PUT."""
        mock_conn = mock.MagicMock()
        mock_conn.admin_virtual_interfaces.return_value = (503, "ERROR!")
        mock_nova.return_value = mock_conn
        req = webob.Request.blank("/v2/ports/random_port_id", method="PUT")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req, fail="nova")

        self.assertFalse(mock_neutron.called)
        self.assertTrue(mock_nova.called)
        self.assertTrue(mock_conn.admin_virtual_interfaces.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, 500)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_delete_to_ports(self, mock_neutron, mock_nova):
        mock_neutron_conn = mock.MagicMock()
        mock_neutron_conn.ports.return_value = self.neutron_response
        mock_neutron.return_value = mock_neutron_conn
        mock_nova_conn = mock.MagicMock()
        mock_nova_conn.admin_virtual_interfaces.return_value = (
            self.nova_response)
        mock_nova.return_value = mock_nova_conn
        req = webob.Request.blank("/v2/ports/random_port_id", method="DELETE")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req)

        self.assertTrue(mock_neutron.called)
        self.assertTrue(mock_neutron_conn.ports.called)
        self.assertTrue(mock_nova.called)
        self.assertTrue(mock_nova_conn.admin_virtual_interfaces.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, fake_resp.status_code)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_delete_to_ports_fail_on_neutron(self, mock_neutron, mock_nova):
        """Test DELETE to /ports failing on Neutron callback.

           Delete includes a call to Neutron, so two failure tests needed.
        """

        mock_neutron_conn = mock.MagicMock()
        mock_neutron_conn.ports.return_value = (503, "ERROR!")
        mock_neutron.return_value = mock_neutron_conn
        req = webob.Request.blank("/v2/ports/random_port_id", method="DELETE")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req, fail="neutron")

        self.assertTrue(mock_neutron.called)
        self.assertTrue(mock_neutron_conn.ports.called)
        self.assertFalse(mock_nova.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, 500)

    @mock.patch("wafflehaus.neutron.nova_interaction.NovaConn")
    @mock.patch("wafflehaus.neutron.nova_interaction.NeutronConn")
    def test_delete_to_ports_fail_on_nova(self, mock_neutron, mock_nova):
        mock_neutron_conn = mock.MagicMock()
        mock_neutron_conn.ports.return_value = self.neutron_response
        mock_neutron.return_value = mock_neutron_conn
        mock_nova_conn = mock.MagicMock()
        mock_nova_conn.admin_virtual_interfaces.return_value = (502, "ERROR!")
        mock_nova.return_value = mock_nova_conn
        req = webob.Request.blank("/v2/ports/random_port_id", method="DELETE")
        test_filter = nova_interaction.filter_factory(self.conf)(self.fake_app)
        resp = test_filter(req)
        fake_resp = self.fake_response(req, fail="nova")

        self.assertTrue(mock_neutron.called)
        self.assertTrue(mock_neutron_conn.ports.called)
        self.assertTrue(mock_nova.called)
        self.assertTrue(mock_nova_conn.admin_virtual_interfaces.called)
        self.assertEqual(resp.json, fake_resp.json)
        self.assertEqual(resp.status_code, 500)
