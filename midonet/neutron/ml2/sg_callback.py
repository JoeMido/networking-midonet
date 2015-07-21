# Copyright (c) 2015 
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

from oslo_log import helpers as log_helpers
from oslo_log import log as logging

from neutron.callbacks import events
from neutron.callbacks import registry
from neutron.callbacks import resources


LOG = logging.getLogger(__name__)


class MidonetSecurityGroupsHandler(object):

    def __init__(self, api_client):
        self.api_cli = api_client
        self.subscribe()

    @log_helpers.log_method_call
    def create_security_group(self, resource, event, trigger, **kwargs):
        security_group = kwargs.get('security_group')
        self.api_cli.create_security_group(security_group)

    @log_helpers.log_method_call
    def update_security_group(self, resource, event, trigger, **kwargs):
        pass

    @log_helpers.log_method_call
    def delete_security_group(self, resource, event, trigger, **kwargs):
        security_group_id = kwargs.get('security_group_id')
        self.api_cli.delete_security_group_rule(security_group_id)

    @log_helpers.log_method_call
    def create_security_group_rule(self, resource, event, trigger, **kwargs):
        security_group_rule = kwargs.get('security_group_rule')
        self.api_cli.create_security_group_rule(security_group_rule)

    @log_helpers.log_method_call
    def delete_security_group_rule(self, resource, event, trigger, **kwargs):
        security_group_rule_id = kwargs.get('security_group_rule_id')
        self.api_cli.delete_security_group_rule(security_group_rule_id)

    def subscribe(self):
        registry.subscribe(
            self.create_security_group, resources.SECURITY_GROUP, events.AFTER_CREATE)
        registry.subscribe(
            self.update_security_group, resources.SECURITY_GROUP, events.AFTER_UPDATE)
        registry.subscribe(
            self.delete_security_group, resources.SECURITY_GROUP, events.AFTER_DELETE)
        registry.subscribe(
            self.create_security_group_rule, resources.SECURITY_GROUP_RULE,
            events.AFTER_CREATE)
        registry.subscribe(
            self.delete_security_group_rule, resources.SECURITY_GROUP_RULE,
            events.AFTER_DELETE)

