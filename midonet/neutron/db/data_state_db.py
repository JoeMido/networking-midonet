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

import datetime
from midonet.neutron.db import db_util
from neutron.db import model_base
import sqlalchemy as sa


DATA_STATE_TABLE = 'midonet_data_state'


class DataState(model_base.BASEV2):
    __tablename__ = DATA_STATE_TABLE
    id = sa.Column(sa.Integer(), primary_key=True)
    last_processed_task_id = sa.Column(sa.Integer(),
                                       sa.ForeignKey('midonet_tasks.id'))
    updated_at = sa.Column(sa.DateTime(), nullable=False)
    active_version = sa.Column(sa.Integer())
    readonly = sa.Column(sa.Boolean(), nullable=False)


def get_data_state(session):
    try:
        return session.query(DataState).one()
    except sa.orm.exc.NoResultFound:
        issue = "Missing Data State table"
        raise db_util.InvalidMidonetDataState(issue)
    except sa.orm.exc.MultipleResultsFound:
        issue = "There should be exactly one Data State table"
        raise db_util.InvalidMidonetDataState(issue)


def get_active_version(session):
    ds = get_data_state(session)
    return ds.active_version


def update_active_version(session, version_id):
    session.query(DataState).update(
        {'active_version': version_id,
         'updated_at': datetime.datetime.utcnow()})


def get_last_processed_task_id(session):
    ds = get_data_state(session)
    return ds.last_processed_task_id


def is_task_table_readonly(session):
    ds = get_data_state(session)
    return ds.readonly


def set_data_state_readonly(session, val):
    session.query(DataState).update(
        {'readonly': val, 'updated_at': datetime.datetime.utcnow()})
    session.commit()


def set_readonly(session):
    set_data_state_readonly(session, True)


def set_readwrite(session):
    set_data_state_readonly(session, False)