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


PORT_BINDING_TABLE_NAME = 'midonet_port_binding'


class PortBinding(model_base.BASEV2):
    __tablename__ = PORT_BINDING_TABLE_NAME
    id = sa.Column(sa.String(length=36), primary_key=True)
    port_id = sa.Column(sa.String(length=36), nullable=False)
    host_id = sa.Column(sa.String(length=36), nullable=False)
    sa.Column(sa.String(length=16), nullable=False)
