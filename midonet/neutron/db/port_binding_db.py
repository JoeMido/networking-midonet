# Copyright 2015 Midokura SARL
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
from neutron.db import models_v2
from neutron.extensions import portbindings
import sqlalchemy as sa
from sqlalchemy import orm


class PortBinding(model_base.BASEV2):
    __tablename__ = 'midonet_port_bindings'

    port_id = sa.Column(sa.String(36),
                        sa.ForeignKey('ports.id', ondelete="CASCADE"),
                        primary_key=True)
    interface_name = sa.Column(sa.String(length=255), nullable=False)
    port = orm.relationship(models_v2.Port,
                            backref=orm.backref("midoportbinding", lazy='joined',
                                                uselist=False,
                                                cascade='delete'))

class MidonetPortBindingMixin(object):

    def _update_midonet_port_binding(self, context, port_data):
        binding_profile = port_data.get(portbindings.PROFILE)
        if binding_profile is None:
            return
        interface_name = binding_profile.get('if_name')
        if interface_name is None:
            return
        context.session.add(PortBinding(port_id=port_data['id'],
                                        interface_name=interface_name))
