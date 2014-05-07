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
from tests import test_base
import webob.dec

from wafflehaus.neutron.api import adaptor


class DummyApiApp(object):

    @webob.dec.wsgify
    def __call__(self, req):
        return req.path


class TestAPIAdaptor(test_base.TestBase):

    def setUp(self):
        self.app = DummyApiApp()

        self.conf = {'enabled': 'true'}

        self.default_mock = mock.Mock()
        self.default_mock.return_value = self.app

    def test_use_filter_factory(self):
        result = adaptor.filter_factory({})(self.app)
        self.assertIsNotNone(result)

    def test_do_nothing_not_enabled(self):
        result = adaptor.filter_factory({})(self.app)
        pkg = 'wafflehaus.neutron.api.adaptor.APIAdaptor'
        with patch(pkg + '._execute_request', self.default_mock) as mock:
            resp = result.__call__.request('/v2.0/allocate_for_instance',
                                           method='POST', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)

    def test_do_not_execute_on_incorrect_resource(self):
        result = adaptor.filter_factory(self.conf)(self.app)
        pkg = 'wafflehaus.neutron.api.adaptor.APIAdaptor'
        with patch(pkg + '._execute_request', self.default_mock) as mock:
            resp = result.__call__.request('/v2.0/allocate_for_instance',
                                           method='GET', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)
            resp = result.__call__.request('/v2.0/allocate_for_instance',
                                           method='PUT', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)
            resp = result.__call__.request('/v2.0/allocate_for_instance',
                                           method='DELETE', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)
            resp = result.__call__.request('/v2.0/allocate_for_instances',
                                           method='POST', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)
            resp = result.__call__.request('/v2.0/allocate_for_instnce',
                                           method='POST', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)
            resp = result.__call__.request('/allocate_for_instance',
                                           method='POST', body=None)
            self.assertFalse(mock.called)
            self.assertEqual(self.app, resp)

    def test_afi_execute_on_correct_resource(self):
        result = adaptor.filter_factory(self.conf)(self.app)
        pkg = 'wafflehaus.neutron.api.adaptor.APIAdaptor'
        with patch(pkg + '._allocate_for_instance', self.default_mock) as mock:
            resp = result.__call__.request('/v2.0/allocate_for_instance',
                                           method='POST', body=None)
            self.assertTrue(mock.called)
            self.assertEqual(self.app, resp)

    def test_afi_does_stuff(self):
        result = adaptor.filter_factory(self.conf)(self.app)
        resp = result.__call__.request('/v2.0/allocate_for_instance',
                                       method='POST', body=None)
        self.assertEqual('/v2.0/allocate_for_instance', resp)

    def test_ginw_execute_on_correct_resource(self):
        result = adaptor.filter_factory(self.conf)(self.app)
        pkg = 'wafflehaus.neutron.api.adaptor.APIAdaptor'
        with patch(pkg + '._get_instance_nw_info', self.default_mock) as mock:
            result.__call__.request('/v2.0/get_instance_nw_info',
                                    method='GET', body=None)
            self.assertTrue(mock.called)
