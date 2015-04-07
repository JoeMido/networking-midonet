# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright (C) 2014 Midokura SARL.
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

import re
import time
from webob import exc as w_exc

from midonetclient import exc

from neutron.api.v2 import base
from neutron.common import exceptions as n_exc
from neutron import i18n
from oslo_log import log as logging


LOG = logging.getLogger(__name__)
PLURAL_NAME_MAP = {}
_LW = i18n._LW


def handle_api_error(fn):
    """Wrapper for methods that throws custom exceptions."""
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (w_exc.HTTPException, exc.MidoApiConnectionError) as ex:
            raise MidonetApiException(msg=ex)
    return wrapped


def retry_on_error(attempts, delay, error_cls):
    """Decorator for error handling retry logic

    This decorator retries the function specified number of times with
    specified delay between each attempt, for every exception thrown specified
    in error_cls.  If case the retry fails in all attempts, the error_cls
    exception object is thrown.

    :param attempts: Number of retry attempts
    :param delay: Delay in seconds between attempts
    :param error_cls: The exception class that triggers a retry attempt
    """
    def internal_wrapper(func):
        def retry(*args, **kwargs):
            err = None
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except error_cls as exc:
                    LOG.warn(_LW('Retrying because of error: %r'), exc)
                    time.sleep(delay)
                    err = exc
            # err should always be set to a valid exception object
            assert isinstance(err, error_cls)
            raise err
        return retry
    return internal_wrapper


class MidonetApiException(n_exc.NeutronException):
        message = _("MidoNet API error: %(msg)s")


class MidonetPluginException(n_exc.NeutronException):
    message = _("%(msg)s")


def generate_methods(*methods):
    """Decorator for classes that represents which methods are required by the
    classes.

    :param methods: The list of methods to be generated automatically. They
                    must be some or one of 'list', 'show', 'create', 'update'
                    and 'delete'.
    """

    @handle_api_error
    def create_resource(self, context, resource):
        pass

    @handle_api_error
    def update_resource(self, context, id, resource):
        pass

    @handle_api_error
    def get_resource(self, context, id, fields=None):
        pass

    @handle_api_error
    def get_resources(self, context, filters=None, fields=None):
        pass

    @handle_api_error
    def delete_resource(self, context, id):
        pass

    AVAILABLE_METHOD_MAP = {base.Controller.LIST: get_resources,
                            base.Controller.SHOW: get_resource,
                            base.Controller.CREATE: create_resource,
                            base.Controller.UPDATE: update_resource,
                            base.Controller.DELETE: delete_resource}
    ALLOWED_METHODS = AVAILABLE_METHOD_MAP.keys()

    required_methods = [method for method in methods
                        if method in ALLOWED_METHODS]

    def wrapper(cls):
        # Use the first capitalzed word as an alias.
        try:
            alias = getattr(cls, 'ALIAS')
        except AttributeError:
            [capitalized_resource] = re.findall(
                '^[A-Z][a-z0-9_]*', cls.__name__)
            alias = capitalized_resource.lower()
            setattr(cls, 'ALIAS', alias)
        parent = getattr(cls, 'PARENT', None)
        if parent:
            alias = '%s_%s' % (parent, alias)
        for method in required_methods:
            if method in [base.Controller.LIST, base.Controller.SHOW]:
                if method == base.Controller.LIST:
                    pluralized_alias = PLURAL_NAME_MAP.get(
                        alias, '%ss' % alias)
                    method_name = 'get_' + pluralized_alias
                else:
                    method_name = 'get_' + alias
            else:
                method_name = method + '_' + alias
            try:
                getattr(cls, method_name)
                abstract_methods = getattr(cls, '__abstractmethods__', None)
                if abstract_methods is not None and (
                        method_name in abstract_methods):
                    setattr(cls, method_name, AVAILABLE_METHOD_MAP[method])
                    implemented_method = frozenset([method_name])
                    abstract_methods = abstract_methods - implemented_method
                    setattr(cls, '__abstractmethods__', abstract_methods)
            except AttributeError:
                setattr(cls, method_name, AVAILABLE_METHOD_MAP[method])
        return cls

    return wrapper
