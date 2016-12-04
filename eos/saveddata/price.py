# ===============================================================================
# Copyright (C) 2010 Diego Duclos
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

import time

from sqlalchemy.orm import reconstructor

from eos.db import saveddata_session, sd_lock
from eos.db.saveddata.queries import cachedQuery


class Price(object):
    def __init__(self, typeID):
        self.typeID = typeID
        self.time = 0
        self.price = 0
        self.failed = None
        self.__item = None

    @reconstructor
    def init(self):
        self.__item = None

    @property
    def isValid(self):
        return self.time >= time.time()



@cachedQuery(Price, 1, "typeID")
def getPrice(typeID):
    if isinstance(typeID, int):
        with sd_lock:
            price = saveddata_session.query(Price).get(typeID)
    else:
        raise TypeError("Need integer as argument")
    return price


def clearPrices():
    with sd_lock:
        deleted_rows = saveddata_session.query(Price).delete()
    commit()
    return deleted_rows

