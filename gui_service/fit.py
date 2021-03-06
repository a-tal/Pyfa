# ===============================================================================
# Copyright (C) 2010 Diego Duclos
#
# This file is part of pyfa.
#
# pyfa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfa.  If not, see <http://www.gnu.org/licenses/>.
# ===============================================================================


import copy
import logging

from gui_service.character import Character
from gui_service.fleet import Fleet
from gui_service.market import Market
from gui_service.settings import SettingsProvider

from eos.db.sqlAlchemy import sqlAlchemy
from eos.db.saveddata import queries as eds_queries
from eos.gamedata import getItem
from eos.saveddata.booster import Booster as es_Booster
from eos.saveddata.cargo import Cargo as es_Cargo
from eos.saveddata.character import Character as saveddata_Character, getCharacter
from eos.saveddata.citadel import Citadel as es_Citadel
from eos.saveddata.damagePattern import DamagePattern as es_DamagePattern
from eos.saveddata.drone import Drone as es_Drone
from eos.saveddata.fighter import Fighter as es_Fighter
from eos.saveddata.fit import Fit as es_Fit, getFit, getBoosterFits, getFitList, getFitsWithShip
from eos.saveddata.fit import countAllFits, countFitsWithShip, searchFits
from eos.saveddata.implant import Implant as es_Implant
from eos.saveddata.module import Module as es_Module
from eos.saveddata.module import Slot as Slot, Module as Module, State as State
from eos.saveddata.ship import Ship as es_Ship
from gui_service.damagePattern import DamagePattern as s_DamagePattern

logger = logging.getLogger(__name__)


class Fit(object):
    instance = None

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls.instance = Fit()

        return cls.instance

    def __init__(self):
        # TODO: This is broken. Import cleanup.
        # self.pattern = DamagePattern.getInstance().getDamagePattern("Uniform")
        # self.pattern = DamagePattern.getDamagePattern(DamagePattern.getInstance(),"Uniform")

        self.targetResists = None
        self.character = saveddata_Character.getAll5()
        self.booster = False
        self.dirtyFitIDs = set()

        serviceFittingDefaultOptions = {
            "useGlobalCharacter": False,
            "useGlobalDamagePattern": False,
            "defaultCharacter": self.character.ID,
            "useGlobalForceReload": False,
            "colorFitBySlot": False,
            "rackSlots": True,
            "rackLabels": True,
            "compactSkills": True,
            "showTooltip": True,
            "showMarketShortcuts": False,
            "enableGaugeAnimation": True,
            "exportCharges": True,
            "openFitInNew": False,
        }

        self.serviceFittingOptions = SettingsProvider.getInstance().getSettings(
            "pyfaServiceFittingOptions", serviceFittingDefaultOptions)

    def getAllFits(self):
        fits = getFitList()
        names = []
        for fit in fits:
            names.append((fit.ID, fit.name))

        return names

    def getFitsWithShip(self, shipID):
        """ Lists fits of shipID, used with shipBrowser """
        fits = getFitsWithShip(shipID)
        names = []
        for fit in fits:
            names.append((fit.ID, fit.name, fit.booster, fit.timestamp))

        return names

    def getBoosterFits(self):
        """ Lists fits flagged as booster """
        fits = getBoosterFits()
        names = []
        for fit in fits:
            names.append((fit.ID, fit.name, fit.shipID))

        return names

    def countAllFits(self):
        return countAllFits()

    def countFitsWithShip(self, shipID):
        count = countFitsWithShip(shipID)
        return count

    def groupHasFits(self, groupID):
        sMkt = Market.getInstance()
        grp = sMkt.getGroup(groupID)
        items = sMkt.getItemsByGroup(grp)
        for item in items:
            if self.countFitsWithShip(item.ID) > 0:
                return True
        return False

    def getModule(self, fitID, pos):
        fit = getFit(fitID)
        return fit.modules[pos]

    def newFit(self, shipID, name=None):
        try:
            ship = es_Ship(getItem(shipID))
        except ValueError:
            ship = es_Citadel(getItem(shipID))
        fit = es_Fit(ship)
        fit.name = name if name is not None else "New %s" % fit.ship.item.name
        fit.damagePattern = self.pattern
        fit.targetResists = self.targetResists
        fit.character = self.character
        fit.booster = self.booster
        eds_queries.save(fit)
        self.recalc(fit)
        return fit.ID

    def toggleBoostFit(self, fitID):
        fit = getFit(fitID)
        fit.booster = not fit.booster
        eds_queries.commit()

    def renameFit(self, fitID, newName):
        fit = getFit(fitID)
        fit.name = newName
        eds_queries.commit()

    def deleteFit(self, fitID):
        fit = getFit(fitID)
        sFleet = Fleet.getInstance()
        sFleet.removeAssociatedFleetData(fit)

        eds_queries.remove(fit)

        # refresh any fits this fit is projected onto. Otherwise, if we have
        # already loaded those fits, they will not reflect the changes
        for projection in fit.projectedOnto.values():
            if projection.victim_fit in sqlAlchemy.saveddata_session:  # GH issue #359
                sqlAlchemy.saveddata_session.refresh(projection.victim_fit)

    def copyFit(self, fitID):
        fit = getFit(fitID)
        newFit = copy.deepcopy(fit)
        eds_queries.save(newFit)
        return newFit.ID

    def clearFit(self, fitID):
        if fitID is None:
            return None

        fit = getFit(fitID)
        fit.clear()
        return fit

    def toggleFactorReload(self, fitID):
        if fitID is None:
            return None

        fit = getFit(fitID)
        fit.factorReload = not fit.factorReload
        eds_queries.commit()
        self.recalc(fit)

    def switchFit(self, fitID):
        if fitID is None:
            return None

        fit = getFit(fitID)

        if self.serviceFittingOptions["useGlobalCharacter"]:
            if fit.character != self.character:
                fit.character = self.character

        if self.serviceFittingOptions["useGlobalDamagePattern"]:
            if fit.damagePattern != self.pattern:
                fit.damagePattern = self.pattern

        eds_queries.commit()
        self.recalc(fit, withBoosters=True)

    def getFit(self, fitID, projected=False, basic=False):
        ''' Gets fit from database, and populates fleet data.
        Projected is a recursion flag that is set to reduce recursions into projected fits
        Basic is a flag to simply return the fit without any other processing
        '''
        if fitID is None:
            return None
        fit = getFit(fitID)

        if basic:
            return fit

        inited = getattr(fit, "inited", None)

        if inited is None or inited is False:
            sFleet = Fleet.getInstance()
            f = sFleet.getLinearFleet(fit)
            if f is None:
                sFleet.removeAssociatedFleetData(fit)
                fit.fleet = None
            else:
                fit.fleet = f

            if not projected:
                for fitP in fit.projectedFits:
                    self.getFit(fitP.ID, projected=True)
                self.recalc(fit, withBoosters=True)
                fit.fill()

            # Check that the states of all modules are valid
            self.checkStates(fit, None)

            eds_queries.commit()
            fit.inited = True
        return fit

    def searchFits(self, name):
        results = searchFits(name)
        fits = []
        for fit in results:
            fits.append((
                fit.ID, fit.name, fit.ship.item.ID, fit.ship.item.name, fit.booster,
                fit.timestamp))
        return fits

    def addImplant(self, fitID, itemID, recalc=True):
        if fitID is None:
            return False

        fit = getFit(fitID)
        item = getItem(itemID, eager="attributes")
        try:
            implant = es_Implant(item)
        except ValueError:
            return False

        fit.implants.append(implant)
        if recalc:
            self.recalc(fit)
        return True

    def removeImplant(self, fitID, position):
        if fitID is None:
            return False

        fit = getFit(fitID)
        implant = fit.implants[position]
        fit.implants.remove(implant)
        self.recalc(fit)
        return True

    def addBooster(self, fitID, itemID):
        if fitID is None:
            return False

        fit = getFit(fitID)
        item = getItem(itemID, eager="attributes")
        try:
            booster = es_Booster(item)
        except ValueError:
            return False

        fit.boosters.append(booster)
        self.recalc(fit)
        return True

    def removeBooster(self, fitID, position):
        if fitID is None:
            return False

        fit = getFit(fitID)
        booster = fit.boosters[position]
        fit.boosters.remove(booster)
        self.recalc(fit)
        return True

    def project(self, fitID, thing):
        if fitID is None:
            return

        fit = getFit(fitID)

        if isinstance(thing, int):
            thing = getItem(thing,
                            eager=("attributes", "group.category"))

        if isinstance(thing, es_Fit):
            if thing in fit.projectedFits:
                return

            fit.__projectedFits[thing.ID] = thing

            # this bit is required -- see GH issue # 83
            sqlAlchemy.saveddata_session.flush()
            sqlAlchemy.saveddata_session.refresh(thing)
        elif thing.category.name == "Drone":
            drone = None
            for d in fit.projectedDrones.find(thing):
                if d is None or d.amountActive == d.amount or d.amount >= 5:
                    drone = d
                    break

            if drone is None:
                drone = es_Drone(thing)
                fit.projectedDrones.append(drone)

            drone.amount += 1
        elif thing.category.name == "Fighter":
            fighter = es_Fighter(thing)
            fit.projectedFighters.append(fighter)
        elif thing.group.name == "Effect Beacon":
            module = es_Module(thing)
            module.state = State.ONLINE
            fit.projectedModules.append(module)
        else:
            module = es_Module(thing)
            module.state = State.ACTIVE
            if not module.canHaveState(module.state, fit):
                module.state = State.OFFLINE
            fit.projectedModules.append(module)

        eds_queries.commit()
        self.recalc(fit)
        return True

    def addCommandFit(self, fitID, thing):
        if fitID is None:
            return

        fit = getFit(fitID)

        if thing in fit.commandFits:
            return

        fit.__commandFits[thing.ID] = thing

        # this bit is required -- see GH issue # 83
        sqlAlchemy.saveddata_session.flush()
        sqlAlchemy.saveddata_session.refresh(thing)

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleProjected(self, fitID, thing, click):
        fit = getFit(fitID)
        if isinstance(thing, es_Drone):
            if thing.amountActive == 0 and thing.canBeApplied(fit):
                thing.amountActive = thing.amount
            else:
                thing.amountActive = 0
        elif isinstance(thing, es_Fighter):
            thing.active = not thing.active
        elif isinstance(thing, es_Module):
            thing.state = self.__getProposedState(thing, click)
            if not thing.canHaveState(thing.state, fit):
                thing.state = State.OFFLINE
        elif isinstance(thing, es_Fit):
            projectionInfo = thing.getProjectionInfo(fitID)
            if projectionInfo:
                projectionInfo.active = not projectionInfo.active

        eds_queries.commit()
        self.recalc(fit)

    def toggleCommandFit(self, fitID, thing):
        fit = getFit(fitID)
        commandInfo = thing.getCommandInfo(fitID)
        if commandInfo:
            commandInfo.active = not commandInfo.active

        eds_queries.commit()
        self.recalc(fit)

    def changeAmount(self, fitID, projected_fit, amount):
        """Change amount of projected fits"""
        fit = getFit(fitID)
        amount = min(20, max(1, amount))  # 1 <= a <= 20
        projectionInfo = projected_fit.getProjectionInfo(fitID)
        if projectionInfo:
            projectionInfo.amount = amount

        eds_queries.commit()
        self.recalc(fit)

    def changeActiveFighters(self, fitID, fighter, amount):
        fit = getFit(fitID)
        fighter.amountActive = amount

        eds_queries.commit()
        self.recalc(fit)

    def removeProjected(self, fitID, thing):
        fit = getFit(fitID)
        if isinstance(thing, es_Drone):
            fit.projectedDrones.remove(thing)
        elif isinstance(thing, es_Module):
            fit.projectedModules.remove(thing)
        elif isinstance(thing, es_Fighter):
            fit.projectedFighters.remove(thing)
        else:
            del fit.__projectedFits[thing.ID]
            # fit.projectedFits.remove(thing)

        eds_queries.commit()
        self.recalc(fit)

    def removeCommand(self, fitID, thing):
        fit = getFit(fitID)
        del fit.__commandFits[thing.ID]

        eds_queries.commit()
        self.recalc(fit)

    def appendModule(self, fitID, itemID):
        fit = getFit(fitID)
        item = getItem(itemID, eager=("attributes", "group.category"))
        try:
            m = es_Module(item)
        except ValueError:
            return False

        if m.item.category.name == "Subsystem":
            fit.modules.freeSlot(m.getModifiedItemAttr("subSystemSlot"))

        if m.fits(fit):
            m.owner = fit
            numSlots = len(fit.modules)
            fit.modules.append(m)
            if m.isValidState(State.ACTIVE):
                m.state = State.ACTIVE

            # As some items may affect state-limiting attributes of the ship, calculate new attributes first
            self.recalc(fit)
            # Then, check states of all modules and change where needed. This will recalc if needed
            self.checkStates(fit, m)

            fit.fill()
            eds_queries.commit()

            return numSlots != len(fit.modules)
        else:
            return None

    def removeModule(self, fitID, position):
        fit = getFit(fitID)
        if fit.modules[position].isEmpty:
            return None

        numSlots = len(fit.modules)
        fit.modules.toDummy(position)
        self.recalc(fit)
        self.checkStates(fit, None)
        fit.fill()
        eds_queries.commit()
        return numSlots != len(fit.modules)

    def changeModule(self, fitID, position, newItemID):
        fit = getFit(fitID)

        # Dummy it out in case the next bit fails
        fit.modules.toDummy(position)

        item = getItem(newItemID, eager=("attributes", "group.category"))
        try:
            m = es_Module(item)
        except ValueError:
            return False

        if m.fits(fit):
            m.owner = fit
            fit.modules.toModule(position, m)
            if m.isValidState(State.ACTIVE):
                m.state = State.ACTIVE

            # As some items may affect state-limiting attributes of the ship, calculate new attributes first
            self.recalc(fit)
            # Then, check states of all modules and change where needed. This will recalc if needed
            self.checkStates(fit, m)

            fit.fill()
            eds_queries.commit()

            return True
        else:
            return None

    def moveCargoToModule(self, fitID, moduleIdx, cargoIdx, copyMod=False):
        """
        Moves cargo to fitting window. Can either do a copy, move, or swap with current module
        If we try to copy/move into a spot with a non-empty module, we swap instead.
        To avoid redundancy in converting Cargo item, this function does the
        sanity checks as opposed to the GUI View. This is different than how the
        normal .swapModules() does things, which is mostly a blind swap.
        """
        fit = getFit(fitID)

        module = fit.modules[moduleIdx]
        cargo = fit.cargo[cargoIdx]

        # Gather modules and convert Cargo item to Module, silently return if not a module
        try:
            cargoP = Module(cargo.item)
            cargoP.owner = fit
            if cargoP.isValidState(State.ACTIVE):
                cargoP.state = State.ACTIVE
        except:
            return

        if cargoP.slot != module.slot:  # can't swap modules to different racks
            return

        # remove module that we are trying to move cargo to
        fit.modules.remove(module)

        if not cargoP.fits(fit):  # if cargo doesn't fit, rollback and return
            fit.modules.insert(moduleIdx, module)
            return

        fit.modules.insert(moduleIdx, cargoP)

        if not copyMod:  # remove existing cargo if not cloning
            if cargo.amount == 1:
                fit.cargo.remove(cargo)
            else:
                cargo.amount -= 1

        if not module.isEmpty:  # if module is placeholder, we don't want to convert/add it
            for x in fit.cargo.find(module.item):
                x.amount += 1
                break
            else:
                moduleP = es_Cargo(module.item)
                moduleP.amount = 1
                fit.cargo.insert(cargoIdx, moduleP)

        eds_queries.commit()
        self.recalc(fit)

    def swapModules(self, fitID, src, dst):
        fit = getFit(fitID)
        # Gather modules
        srcMod = fit.modules[src]
        dstMod = fit.modules[dst]

        # To swap, we simply remove mod and insert at destination.
        fit.modules.remove(srcMod)
        fit.modules.insert(dst, srcMod)
        fit.modules.remove(dstMod)
        fit.modules.insert(src, dstMod)

        eds_queries.commit()

    def cloneModule(self, fitID, src, dst):
        """
        Clone a module from src to dst
        This will overwrite dst! Checking for empty module must be
        done at a higher level
        """
        fit = getFit(fitID)
        # Gather modules
        srcMod = fit.modules[src]
        dstMod = fit.modules[dst]  # should be a placeholder module

        new = copy.deepcopy(srcMod)
        new.owner = fit
        if new.fits(fit):
            # insert copy if module meets hardpoint restrictions
            fit.modules.remove(dstMod)
            fit.modules.insert(dst, new)

            eds_queries.commit()
            self.recalc(fit)

    def addCargo(self, fitID, itemID, amount=1, replace=False):
        """
        Adds cargo via typeID of item. If replace = True, we replace amount with
        given parameter, otherwise we increment
        """

        if fitID is None:
            return False

        fit = getFit(fitID)
        item = getItem(itemID)
        cargo = None

        # adding from market
        for x in fit.cargo.find(item):
            if x is not None:
                # found item already in cargo, use previous value and remove old
                cargo = x
                fit.cargo.remove(x)
                break

        if cargo is None:
            # if we don't have the item already in cargo, use default values
            cargo = es_Cargo(item)

        fit.cargo.append(cargo)
        if replace:
            cargo.amount = amount
        else:
            cargo.amount += amount

        self.recalc(fit)
        eds_queries.commit()

        return True

    def removeCargo(self, fitID, position):
        if fitID is None:
            return False

        fit = getFit(fitID)
        charge = fit.cargo[position]
        fit.cargo.remove(charge)
        self.recalc(fit)
        return True

    def addFighter(self, fitID, itemID):
        if fitID is None:
            return False

        fit = getFit(fitID)
        item = getItem(itemID, eager=("attributes", "group.category"))
        if item.category.name == "Fighter":
            fighter = None
            '''
            for d in fit.fighters.find(item):
                if d is not None and d.amountActive == 0 and d.amount < max(5, fit.extraAttributes["maxActiveDrones"]):
                    drone = d
                    break
            '''
            if fighter is None:
                fighter = es_Fighter(item)
                used = fit.getSlotsUsed(fighter.slot)
                total = fit.getNumSlots(fighter.slot)
                standardAttackActive = False
                for ability in fighter.abilities:
                    if (ability.effect.isImplemented and ability.effect.handlerName == u'fighterabilityattackm'):
                        # Activate "standard attack" if available
                        ability.active = True
                        standardAttackActive = True
                    else:
                        # Activate all other abilities (Neut, Web, etc) except propmods if no standard attack is active
                        if (ability.effect.isImplemented and
                                standardAttackActive is False and
                                ability.effect.handlerName != u'fighterabilitymicrowarpdrive' and
                                ability.effect.handlerName != u'fighterabilityevasivemaneuvers'):
                            ability.active = True

                if used >= total:
                    fighter.active = False

                if fighter.fits(fit) is True:
                    fit.fighters.append(fighter)
                else:
                    return False

            eds_queries.commit()
            self.recalc(fit)
            return True
        else:
            return False

    def removeFighter(self, fitID, i):
        fit = getFit(fitID)
        f = fit.fighters[i]
        fit.fighters.remove(f)

        eds_queries.commit()
        self.recalc(fit)
        return True

    def addDrone(self, fitID, itemID):
        if fitID is None:
            return False

        fit = getFit(fitID)
        item = getItem(itemID, eager=("attributes", "group.category"))
        if item.category.name == "Drone":
            drone = None
            for d in fit.drones.find(item):
                if d is not None and d.amountActive == 0 and d.amount < max(5, fit.extraAttributes["maxActiveDrones"]):
                    drone = d
                    break

            if drone is None:
                drone = es_Drone(item)
                if drone.fits(fit) is True:
                    fit.drones.append(drone)
                else:
                    return False
            drone.amount += 1
            eds_queries.commit()
            self.recalc(fit)
            return True
        else:
            return False

    def mergeDrones(self, fitID, d1, d2, projected=False):
        if fitID is None:
            return False

        fit = getFit(fitID)
        if d1.item != d2.item:
            return False

        if projected:
            fit.projectedDrones.remove(d1)
        else:
            fit.drones.remove(d1)

        d2.amount += d1.amount
        d2.amountActive += d1.amountActive if d1.amountActive > 0 else -d2.amountActive
        eds_queries.commit()
        self.recalc(fit)
        return True

    def splitDrones(self, fit, d, amount, l):
        total = d.amount
        active = d.amountActive > 0
        d.amount = amount
        d.amountActive = amount if active else 0

        newD = es_Drone(d.item)
        newD.amount = total - amount
        newD.amountActive = newD.amount if active else 0
        l.append(newD)
        eds_queries.commit()

    def splitProjectedDroneStack(self, fitID, d, amount):
        if fitID is None:
            return False

        fit = getFit(fitID)
        self.splitDrones(fit, d, amount, fit.projectedDrones)

    def splitDroneStack(self, fitID, d, amount):
        if fitID is None:
            return False

        fit = getFit(fitID)
        self.splitDrones(fit, d, amount, fit.drones)

    def removeDrone(self, fitID, i, numDronesToRemove=1):
        fit = getFit(fitID)
        d = fit.drones[i]
        d.amount -= numDronesToRemove
        if d.amountActive > 0:
            d.amountActive -= numDronesToRemove

        if d.amount == 0:
            del fit.drones[i]

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleDrone(self, fitID, i):
        fit = getFit(fitID)
        d = fit.drones[i]
        if d.amount == d.amountActive:
            d.amountActive = 0
        else:
            d.amountActive = d.amount

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleFighter(self, fitID, i):
        fit = getFit(fitID)
        f = fit.fighters[i]
        f.active = not f.active

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleImplant(self, fitID, i):
        fit = getFit(fitID)
        implant = fit.implants[i]
        implant.active = not implant.active

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleImplantSource(self, fitID, source):
        fit = getFit(fitID)
        fit.implantSource = source

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleBooster(self, fitID, i):
        fit = getFit(fitID)
        booster = fit.boosters[i]
        booster.active = not booster.active

        eds_queries.commit()
        self.recalc(fit)
        return True

    def toggleFighterAbility(self, fitID, ability):
        fit = getFit(fitID)
        ability.active = not ability.active
        eds_queries.commit()
        self.recalc(fit)

    def changeChar(self, fitID, charID):
        if fitID is None or charID is None:
            if charID is not None:
                self.character = Character.getInstance().all5()

            return

        fit = getFit(fitID)
        fit.character = self.character = getCharacter(charID)
        self.recalc(fit)

    def isAmmo(self, itemID):
        return getItem(itemID).category.name == "Charge"

    def setAmmo(self, fitID, ammoID, modules):
        if fitID is None:
            return

        fit = getFit(fitID)
        ammo = getItem(ammoID) if ammoID else None

        for mod in modules:
            if mod.isValidCharge(ammo):
                mod.charge = ammo

        self.recalc(fit)

    def getTargetResists(self, fitID):
        if fitID is None:
            return

        fit = getFit(fitID)
        return fit.targetResists

    def setTargetResists(self, fitID, pattern):
        if fitID is None:
            return

        fit = getFit(fitID)
        fit.targetResists = pattern
        eds_queries.commit()

        self.recalc(fit)

    def getDamagePattern(self, fitID):
        if fitID is None:
            return

        fit = getFit(fitID)
        return fit.damagePattern

    def setDamagePattern(self, fitID, pattern):
        if fitID is None:
            return

        fit = getFit(fitID)
        fit.damagePattern = self.pattern = pattern
        eds_queries.commit()

        self.recalc(fit)

    def setMode(self, fitID, mode):
        if fitID is None:
            return

        fit = getFit(fitID)
        fit.mode = mode
        eds_queries.commit()

        self.recalc(fit)

    def setAsPattern(self, fitID, ammo):
        if fitID is None:
            return

        sDP = s_DamagePattern.getInstance()
        dp = sDP.getDamagePattern("Selected Ammo")
        if dp is None:
            dp = es_DamagePattern()
            dp.name = "Selected Ammo"

        fit = getFit(fitID)
        for attr in ("em", "thermal", "kinetic", "explosive"):
            setattr(dp, "%sAmount" % attr, ammo.getAttribute("%sDamage" % attr) or 0)

        fit.damagePattern = dp
        self.recalc(fit)

    def checkStates(self, fit, base):
        changed = False
        for mod in fit.modules:
            if mod != base:
                if not mod.canHaveState(mod.state):
                    mod.state = State.ONLINE
                    changed = True
        for mod in fit.projectedModules:
            if not mod.canHaveState(mod.state, fit):
                mod.state = State.OFFLINE
                changed = True
        for drone in fit.projectedDrones:
            if drone.amountActive > 0 and not drone.canBeApplied(fit):
                drone.amountActive = 0
                changed = True

        # If any state was changed, recalculate attributes again
        if changed:
            self.recalc(fit)

    def toggleModulesState(self, fitID, base, modules, click):
        proposedState = self.__getProposedState(base, click)
        if proposedState != base.state:
            base.state = proposedState
            for mod in modules:
                if mod != base:
                    mod.state = self.__getProposedState(mod, click,
                                                        proposedState)

        eds_queries.commit()
        fit = getFit(fitID)

        # As some items may affect state-limiting attributes of the ship, calculate new attributes first
        self.recalc(fit)
        # Then, check states of all modules and change where needed. This will recalc if needed
        self.checkStates(fit, base)

    # Old state : New State
    localMap = {
        State.OVERHEATED: State.ACTIVE,
        State.ACTIVE: State.ONLINE,
        State.OFFLINE: State.ONLINE,
        State.ONLINE: State.ACTIVE}
    projectedMap = {
        State.OVERHEATED: State.ACTIVE,
        State.ACTIVE: State.OFFLINE,
        State.OFFLINE: State.ACTIVE,
        State.ONLINE: State.ACTIVE}  # Just in case
    # For system effects. They should only ever be online or offline
    projectedSystem = {
        State.OFFLINE: State.ONLINE,
        State.ONLINE: State.OFFLINE}

    def __getProposedState(self, mod, click, proposedState=None):
        if mod.slot == Slot.SUBSYSTEM or mod.isEmpty:
            return State.ONLINE

        if mod.slot == Slot.SYSTEM:
            transitionMap = self.projectedSystem
        else:
            transitionMap = self.projectedMap if mod.projected else self.localMap

        currState = mod.state

        if proposedState is not None:
            state = proposedState
        elif click == "right":
            state = State.OVERHEATED
        elif click == "ctrl":
            state = State.OFFLINE
        else:
            state = transitionMap[currState]
            if not mod.isValidState(state):
                state = -1

        if mod.isValidState(state):
            return state
        else:
            return currState

    def refreshFit(self, fitID):
        if fitID is None:
            return None

        fit = getFit(fitID)
        eds_queries.commit()
        self.recalc(fit)

    def recalc(self, fit, withBoosters=True):
        logger.debug("=" * 10 + "recalc" + "=" * 10)
        if fit.factorReload is not self.serviceFittingOptions["useGlobalForceReload"]:
            fit.factorReload = self.serviceFittingOptions["useGlobalForceReload"]
        fit.clear()

        fit.calculateModifiedAttributes(withBoosters=False)
