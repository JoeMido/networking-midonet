# Copyright (C) 2015 Midokura SARL.
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

from neutron.db import model_base
import sqlalchemy as sa	
from midonet.neutron.extensions import agent_membership as ext_am


AGENT_MEMBERSHIP= 'midonet_agent_membership'


class AgentMembership(model_base.BASEV2):
    __tablename__ = AGENT_MEMBERSHIP
    id = sa.Column(sa.String(36), primary_key=True)
    ip_address = sa.Column(sa.String(36)) 


class AgentMembershipDbMixin(ext_am.AgentMembershipPluginBase):
    """Mixin class to add agent membership to db_base_plugin_v2."""

    __native_bulk_support = False

    def _make_agent_membership_dict(self, agent_membership, fields=None):
        res = {'id': agent_membership['id'],
               'tenant_id': agent_membership['tenant_id'],
               'ip_address': agent_membership['ip_address']}
        return self._fields(res, fields)

    def _get_agent_membership(self, context, id):
        try:
            query = self._model_query(context, AgentMembership)
            sg = query.filter(AgentMembership.id == id).one()

        except exc.NoResultFound:
            raise ext_am.AgentMembershipNotFound(id=id)
        return sg

    def create_agent_membership(self, context, agent_membership):
        """Create an agent membership"""
        am = agent_membership['agent_membership']
        tenant_id = self._get_tenant_id_for_create(context, am)

        with context.session.begin(subtransactions=True):
            am_db = AgentMembership(
                id=uuidutils.generate_uuid(), tenant_id=tenant_id,
                agent_id=am['agent_id'], ip_address=am['ip_address'])
            context.session.add(am_db)

        return self._make_agent_membership_dict(am_db)

    def delete_agent_membership(self, context, id):
        am = self._get_agent_membership(context, id)
        with context.session.begin(subtransactions=True):
            context.session.delete(am)

    def get_agent_membership(self, context, id, fields=None):
        return self._make_agent_membership_dict(
            self._get_agent_membership(context, id), fields)

    def get_agent_memberships(self, context, filters=None, fields=None,
                              sorts=None, limit=None, marker=None,
                              page_reverse=False):
        marker_obj = self._get_marker_obj(context, 'agent_membership', limit,
                                          marker)

        return self._get_collection(context,
                                    AgentMembership,
                                    self._make_agent_membership_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts,
                                    limit=limit, marker_obj=marker_obj,
                                    page_reverse=page_reverse)
