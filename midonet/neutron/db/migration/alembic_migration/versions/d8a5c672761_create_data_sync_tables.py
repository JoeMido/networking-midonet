# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""create data sync tables

Revision ID: d8a5c672761
Revises: 7f435b33664
Create Date: 2015-03-16 06:04:40.695379

"""

# revision identifiers, used by Alembic.
revision = 'd8a5c672761'
down_revision = '7f435b33664'

from alembic import op
import datetime
from midonet.neutron.db import task_db
import sqlalchemy as sa


def add_data_versions_table():
    op.create_table(task_db.DATA_VERSIONS_TABLE,
                    sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('sync_started_at', sa.DateTime()),
                    sa.Column('sync_finished_at', sa.DateTime()),
                    sa.Column('sync_status', sa.String(length=50)),
                    sa.Column('sync_tasks_status', sa.String(length=50)),
                    sa.Column('stale', sa.Boolean(), nullable=False))


def add_data_state_table():
    op.create_table(task_db.DATA_STATE_TABLE,
                    sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('last_processed_task_id', sa.Integer()),
                    sa.Column('updated_at', sa.DateTime(),
                              default=datetime.datetime.utcnow,
                              nullable=False),
                    sa.Column('active_version', sa.Integer()),
                    sa.Column('readonly', sa.Boolean(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['last_processed_task_id'], ['midonet_tasks.id']),
                    sa.ForeignKeyConstraint(
                        ['active_version'],
                        [task_db.DATA_VERSIONS_TABLE + '.id']))
    conn = op.get_bind()
    query_str = "select last_processed_id, updated_at from midonet_task_state"
    lp_id, updated_at = conn.execute(query_str).fetchall()[0]
    if lp_id is None:
        lp_id = "NULL"
    op.execute("INSERT INTO %s (id, last_processed_task_id, updated_at, "
               "active_version, readonly) VALUES (1, %s, '%s', NULL, false)"
               % (task_db.DATA_STATE_TABLE, lp_id, updated_at))
    op.drop_table(task_db.TASK_STATE_TABLE)


def remove_data_state_table():
    op.create_table(task_db.TASK_STATE_TABLE,
                    sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('last_processed_id', sa.Integer()),
                    sa.Column('updated_at', sa.DateTime(),
                              default=datetime.datetime.utcnow,
                              nullable=False),
                    sa.ForeignKeyConstraint(['last_processed_id'],
                                            ['midonet_tasks.id']))
    conn = op.get_bind()
    query_str = "select last_processed_task_id, updated_at from %s" % \
                task_db.DATA_STATE_TABLE
    lp_id, updated_at = conn.execute(query_str).fetchall()[0]
    if lp_id is None:
        lp_id = "NULL"
    op.execute("INSERT INTO %s (id, last_processed_id, updated_at) VALUES"
               " (1, %s, '%s')" %
               (task_db.TASK_STATE_TABLE, lp_id, updated_at))
    op.drop_table(task_db.DATA_STATE_TABLE)


def upgrade():
    add_data_versions_table()
    add_data_state_table()


def downgrade():
    remove_data_state_table()
    op.drop_table(task_db.DATA_VERSIONS_TABLE)