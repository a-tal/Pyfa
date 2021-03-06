# ===============================================================================
# Copyright (C) 2016 Ryan Holmes
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

from copy import deepcopy
from sqlalchemy.orm import mapper, relation

from eos.db.sqlAlchemy import sqlAlchemy
from eos.db.saveddata.queries import cachedQuery
from eos.db.util import processEager
from eos.effectHandlerHelpers import HandledImplantBoosterList
from eos.saveddata.targetResists import TargetResists
from eos.db.saveddata.mapper import (
    ImplantSetMap as implantsSetMap_table,
    ImplantSets as implant_set_table
)
# TODO: Import cleanup, shouldn't be a lazy import
import eos.saveddata.implant


class ImplantSet(object):
    def __init__(self, name=None):
        self.name = name
        self.__implants = HandledImplantBoosterList()

        mapper(ImplantSet, implant_set_table,
               properties={
                   "_ImplantSet__implants": relation(
                       eos.saveddata.implant.Implant,
                       collection_class=HandledImplantBoosterList,
                       cascade='all, delete, delete-orphan',
                       backref='set',
                       single_parent=True,
                       primaryjoin=implantsSetMap_table.setID == implant_set_table.ID,
                       secondaryjoin=implantsSetMap_table.implantID == eos.saveddata.implant.Implant.ID,
                       secondary=implantsSetMap_table),
               }
               )

    @property
    def implants(self):
        return self.__implants

    @classmethod
    def exportSets(cls, *sets):
        out = "# Exported from pyfa\n#\n" \
              "# Values are in following format:\n" \
              "# [Implant Set name]\n" \
              "# [Implant name]\n" \
              "# [Implant name]\n" \
              "# ...\n\n"

        for set in sets:
            out += "[{}]\n".format(set.name)
            for implant in set.implants:
                out += "{}\n".format(implant.item.name)
            out += "\n"

        return out.strip()

    def __deepcopy__(self, memo):
        copy = ImplantSet(self.name)
        copy.name = "%s copy" % self.name

        orig = getattr(self, 'implants')
        c = getattr(copy, 'implants')
        for i in orig:
            c.append(deepcopy(i, memo))

        return copy


def getImplantSetList(eager=None):
    eager = processEager(eager)
    with sqlAlchemy.sd_lock:
        sets = sqlAlchemy.saveddata_session.query(ImplantSet).options(*eager).all()
    return sets


@cachedQuery(ImplantSet, 1, "lookfor")
def getImplantSet(lookfor, eager=None):
    if isinstance(lookfor, int):
        if eager is None:
            with sqlAlchemy.sd_lock:
                pattern = sqlAlchemy.saveddata_session.query(ImplantSet).get(lookfor)
        else:
            eager = processEager(eager)
            with sqlAlchemy.sd_lock:
                pattern = sqlAlchemy.saveddata_session.query(ImplantSet).options(*eager).filter(
                    TargetResists.ID == lookfor).first()
    elif isinstance(lookfor, basestring):
        eager = processEager(eager)
        with sqlAlchemy.sd_lock:
            pattern = sqlAlchemy.saveddata_session.query(ImplantSet).options(*eager).filter(TargetResists.name == lookfor).first()
    else:
        raise TypeError("Improper argument")
    return pattern
