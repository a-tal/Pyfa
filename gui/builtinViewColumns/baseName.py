# coding: utf-8
# =============================================================================
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
# =============================================================================

import wx

# TODO: Import refactor. This should not be a lazy import, but it's cyclical and hard to fix :(
import gui.mainFrame
from eos.saveddata.cargo import Cargo as Cargo
from eos.saveddata.drone import Drone as Drone
from eos.saveddata.fighter import Fighter as Fighter
from eos.saveddata.implant import Implant as Implant
from eos.saveddata.module import Slot as Slot, Module as Module, Rack as Rack
from gui.viewColumn import ViewColumn
from service.fit import Fit
from gui.projectedView import ProjectedView
from eos.saveddata.fit import Fit

class BaseName(ViewColumn):
    name = "Base Name"

    def __init__(self, fittingView, params):
        ViewColumn.__init__(self, fittingView)

        self.mainFrame = gui.mainFrame.MainFrame.getInstance()
        self.columnText = "Name"
        self.shipImage = fittingView.imageList.GetImageIndex("ship_small", "gui")
        self.mask = wx.LIST_MASK_TEXT
        self.projectedView = isinstance(fittingView, ProjectedView)

    def getText(self, stuff):
        if isinstance(stuff, Drone):
            return "%dx %s" % (stuff.amount, stuff.item.name)
        elif isinstance(stuff, Fighter):
            return "%d/%d %s" % (stuff.amountActive, stuff.getModifiedItemAttr("fighterSquadronMaxSize"), stuff.item.name)
        elif isinstance(stuff, Cargo):
            return "%dx %s" % (stuff.amount, stuff.item.name)
        elif isinstance(stuff, Fit):
            if self.projectedView:
                # we need a little more information for the projected view
                fitID = self.mainFrame.getActiveFit()
                return "%dx %s (%s)" % (stuff.getProjectionInfo(fitID).amount, stuff.name, stuff.ship.item.name)
            else:
                return "%s (%s)" % (stuff.name, stuff.ship.item.name)
        elif isinstance(stuff, Rack):
            if Fit.getInstance().serviceFittingOptions["rackLabels"]:
                if stuff.slot == Slot.MODE:
                    return u'─ Tactical Mode ─'
                else:
                    return u'─ {} Slots ─'.format(Slot.getName(stuff.slot).capitalize())
            else:
                return ""
        elif isinstance(stuff, Module):
            if stuff.isEmpty:
                return "%s Slot" % Slot.getName(stuff.slot).capitalize()
            else:
                return stuff.item.name
        elif isinstance(stuff, Implant):
            return stuff.item.name
        else:
            item = getattr(stuff, "item", stuff)

            if Fit.getInstance().serviceFittingOptions["showMarketShortcuts"]:
                marketShortcut = getattr(item, "marketShortcut", None)

                if marketShortcut:
                    # use unicode subscript to display shortcut value
                    shortcut = unichr(marketShortcut + 8320) + u" "
                    del item.marketShortcut
                    return shortcut + item.name

            return item.name


BaseName.register()
