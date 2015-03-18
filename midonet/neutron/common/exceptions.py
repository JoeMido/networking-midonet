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

from neutron.common import exceptions


class DataStateReadOnly(exceptions.NeutronException):
    """
    Exception to signify that an attempt was made to write
    to the midonet database while it is locked for reads only
    """
    message = "Midonet Data Base locked"


class TaskTableAccess(exceptions.NeutronException):
    """
    Exception to signify that an attempt was made at accessing the task
    table when the operation was not allowed.
    """
    message = "Unable to access midonet task table"


class InvalidMidonetDataState(exceptions.NeutronException):
    """
    Exception to signify a state in the midonet tables that is invalid,
    i.e. missing some table that should always be present
    """
    message = "Midonet Data in an Invalid State"