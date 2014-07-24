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

from neutron import context

from wafflehaus.try_context.context_filter import BaseContextStrategy


class NeutronContextFilter(BaseContextStrategy):
    def __init__(self, key, req_auth=False):
        super(NeutronContextFilter, self).__init__(key, req_auth)
        self.neutron_ctx = context

    def _process_roles(self, roles):
        if not self.context.roles:
            self.context.roles = []
        if roles is None:
            return
        roles = [r.strip() for r in roles.split(',')]
        for role in roles:
            if role not in self.context.roles:
                self.context.roles.append(role)

    def load_context(self, req):
        super(NeutronContextFilter, self).load_context(req)
        tenant_id = req.headers.get('X_TENANT_ID')
        user_id = req.headers.get('X_USER_NAME')
        if tenant_id is None or user_id is None:
            if self.require_auth_info:
                return False
            ctx = self.neutron_ctx.get_admin_context()
        else:
            ctx = self.neutron_ctx.Context(user_id=user_id,
                                           tenant_id=tenant_id)
        self.context = ctx
        self._process_roles(req.headers.get('X_ROLES', ''))
        req.environ['neutron.context'] = self.context
        return True
