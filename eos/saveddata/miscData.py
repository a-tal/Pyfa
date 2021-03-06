# ===============================================================================
# Copyright (C) 2011 Anton Vorobyov
#
# This file is part of eos.
#
# eos is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# eos is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with eos.  If not, see <http://www.gnu.org/licenses/>.
# ===============================================================================

from eos.db.sqlAlchemy import sqlAlchemy
from eos.eqBase import EqBase
from sqlalchemy.orm import mapper
from eos.db.saveddata.mapper import Miscdata as miscdata_table


class MiscData(EqBase):
    def __init__(self, name, val=None):
        self.fieldName = name
        self.fieldValue = val

        mapper(MiscData, miscdata_table)


def getMiscData(field):
    if isinstance(field, basestring):
        with sqlAlchemy.sd_lock:
            data = sqlAlchemy.saveddata_session.query(MiscData).get(field)
    else:
        raise TypeError("Need string as argument")
    return data
