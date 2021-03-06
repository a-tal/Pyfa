# ===============================================================================
# Copyright (C) 2010 Diego Duclos
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

import logging

from sqlalchemy.orm import reconstructor, mapper
from eos.db.saveddata.mapper import FighterAbilities as fighter_abilities_table

logger = logging.getLogger(__name__)


class FighterAbility(object):
    DAMAGE_TYPES = ("em", "kinetic", "explosive", "thermal")
    DAMAGE_TYPES2 = ("EM", "Kin", "Exp", "Therm")

    # We aren't able to get data on the charges that can be stored with fighters. So we hardcode that data here, keyed
    # with the fighter squadron role
    NUM_SHOTS_MAPPING = {
        1: 0,  # Superiority fighter / Attack
        2: 12,  # Light fighter / Attack
        4: 6,  # Heavy fighter / Heavy attack
        5: 3,  # Heavy fighter / Long range attack
    }
    # Same as above
    REARM_TIME_MAPPING = {
        1: 0,  # Superiority fighter / Attack
        2: 4000,  # Light fighter / Attack
        4: 6000,  # Heavy fighter / Heavy attack
        5: 20000,  # Heavy fighter / Long range attack
    }

    def __init__(self, effect):
        """Initialize from the program"""
        self.__effect = effect
        self.effectID = effect.ID if effect is not None else None
        self.active = False
        self.build()

        mapper(FighterAbility, fighter_abilities_table)

    @reconstructor
    def init(self):
        """Initialize from the database"""
        self.__effect = None

        if self.effectID:
            self.__effect = next((x for x in self.fighter.item.effects.itervalues() if x.ID == self.effectID), None)
            if self.__effect is None:
                logger.error("Effect (id: %d) does not exist", self.effectID)
                return

        self.build()

    def build(self):
        pass

    @property
    def effect(self):
        return self.__effect

    @property
    def name(self):
        return self.__effect.getattr('displayName') or self.__effect.handlerName

    @property
    def attrPrefix(self):
        return self.__effect.getattr('prefix')

    @property
    def dealsDamage(self):
        attr = "{}DamageMultiplier".format(self.attrPrefix)
        return attr in self.fighter.itemModifiedAttributes or self.fighter.charge is not None

    @property
    def grouped(self):
        # is the ability applied per fighter (webs, returns False), or as a group (MWD, returned True)
        return self.__effect.getattr('grouped')

    @property
    def hasCharges(self):
        return self.__effect.getattr('hasCharges')

    @property
    def reloadTime(self):
        return self.fighter.getModifiedItemAttr("fighterRefuelingTime") \
            + (self.REARM_TIME_MAPPING[self.fighter.getModifiedItemAttr("fighterSquadronRole")] or 0 if self.hasCharges else 0) \
            * self.numShots

    @property
    def numShots(self):
        return self.NUM_SHOTS_MAPPING[self.fighter.getModifiedItemAttr("fighterSquadronRole")] or 0 if self.hasCharges else 0

    @property
    def cycleTime(self):
        speed = self.fighter.getModifiedItemAttr("{}Duration".format(self.attrPrefix))

        # Factor in reload
        '''
        reload = self.reloadTime

        if self.fighter.owner.factorReload:
            numShots = self.numShots
            # Speed here already takes into consideration reactivation time
            speed = (speed * numShots + reload) / numShots if numShots > 0 else speed
        '''

        return speed

    def damageStats(self, targetResists=None):
        if self.__dps is None:
            self.__volley = 0
            self.__dps = 0
            if self.dealsDamage and self.active:
                cycleTime = self.cycleTime

                if self.attrPrefix == "fighterAbilityLaunchBomb":
                    # bomb calcs
                    volley = sum(map(lambda attr: (self.fighter.getModifiedChargeAttr("%sDamage" % attr) or 0) * (
                        1 - getattr(targetResists, "%sAmount" % attr, 0)), self.DAMAGE_TYPES))
                else:
                    volley = sum(map(lambda d2, d:
                                     (self.fighter.getModifiedItemAttr(
                                         "{}Damage{}".format(self.attrPrefix, d2)) or 0) *
                                     (1 - getattr(targetResists, "{}Amount".format(d), 0)),
                                     self.DAMAGE_TYPES2, self.DAMAGE_TYPES))

                volley *= self.fighter.amountActive
                volley *= self.fighter.getModifiedItemAttr("{}DamageMultiplier".format(self.attrPrefix)) or 1
                self.__volley += volley
                self.__dps += volley / (cycleTime / 1000.0)

        return self.__dps, self.__volley

    def clear(self):
        self.__dps = None
        self.__volley = None
