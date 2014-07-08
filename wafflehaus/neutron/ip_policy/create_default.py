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

import netaddr
import webob.dec
import webob.exc

from wafflehaus.base import WafflehausBase
import wafflehaus.resource_filter as rf


class DefaultIPPolicy(WafflehausBase):

    def __init__(self, app, conf):
        super(DefaultIPPolicy, self).__init__(app, conf)
        self.log.name = conf.get('log_name', __name__)
        self.log.info('Starting wafflehaus default ip policy middleware')
        self.resource = conf.get('resource', 'POST /v2.0/subnets')
        self.resources = rf.parse_resources(self.resource)

    def _pools_from_ipset(self, ipset):
        cidrs = ipset.iter_cidrs()
        if len(cidrs) == 0:
            return []
        if len(cidrs) == 1:
            return [dict(start=str(cidrs[0][0]),
                         end=str(cidrs[0][-1]))]

        pool_start = cidrs[0][0]
        prev_cidr_end = cidrs[0][-1]
        pools = []
        for cidr in cidrs[1:]:
            cidr_start = cidr[0]
            if prev_cidr_end + 1 != cidr_start:
                pools.append(dict(start=str(pool_start),
                                  end=str(prev_cidr_end)))
                pool_start = cidr_start
            prev_cidr_end = cidr[-1]
        pools.append(dict(start=str(pool_start), end=str(prev_cidr_end)))
        return pools

    def _get_default_allocation_pools(self, subnet):
        alloc_pools = {}
        cidr_net = netaddr.IPNetwork(subnet["cidr"])
        starting_index = 5 if subnet.get("ip_version") == 4 else 10
        start = cidr_net[starting_index]
        end = cidr_net[-2]
        alloc_pools = [{"start": str(start),
                       "end": str(end)}]
        return alloc_pools

    def _modify_allocation_pools(self, subnet):
        alloc_pools = subnet.get('allocation_pools')
        default_alloc_pools = self._get_default_allocation_pools(subnet)
        default_start = netaddr.IPAddress(default_alloc_pools[0]["start"])
        default_end = netaddr.IPAddress(default_alloc_pools[0]["end"])
        default_set = netaddr.IPSet(netaddr.IPRange(default_start,
                                                    default_end).cidrs())
        final_set = netaddr.IPSet()
        for p in alloc_pools:
            start = netaddr.IPAddress(p["start"])
            end = netaddr.IPAddress(p["end"])
            alloc_pool_ip_set = netaddr.IPSet(
                netaddr.IPRange(
                    netaddr.IPAddress(start), netaddr.IPAddress(end)).cidrs())
            final_set.update(default_set & alloc_pool_ip_set)
        alloc_pools = self._pools_from_ipset(final_set)
        return alloc_pools

    def _filter_policy(self, req):
        body = req.body
        try:
            body_json = json.loads(body)
        except ValueError:
            return webob.exc.HTTPBadRequest
        subnets = body_json.get('subnets')
        subnet = body_json.get('subnet')
        body_json["subnets"] = []
        if subnets is None and subnet is None:
            """If this is true there is nothing to work with let app error."""
            return self.app
        single = False
        if subnets is None:
            """If this is true then it's a single, put it in list."""
            single = True
            subnets = [subnet]
        for subnet in subnets:
            alloc_pools = subnet.get('allocation_pools')
            if alloc_pools is None:
                alloc_pools = self._get_default_allocation_pools(subnet)
            else:
                alloc_pools = self._modify_allocation_pools(subnet)
            subnet["allocation_pools"] = alloc_pools
            body_json["subnets"].append(subnet)
        if single:
            body_json["subnet"] = body_json.pop("subnets")[0]
        req.body = json.dumps(body_json)
        self.body = req.body
        return self.app

    @webob.dec.wsgify
    def __call__(self, req):
        super(DefaultIPPolicy, self).__call__(req)
        if not self.enabled:
            return self.app

        if not rf.matched_request(req, self.resources):
            return self.app
        return self._filter_policy(req)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def block_resource(app):
        return DefaultIPPolicy(app, conf)
    return block_resource
