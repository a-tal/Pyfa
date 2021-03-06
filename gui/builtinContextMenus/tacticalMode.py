import wx

import gui.globalEvents as GE
import gui.mainFrame
from gui.contextMenu import ContextMenu
from gui_service.fit import Fit


class TacticalMode(ContextMenu):
    def __init__(self):
        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

    def display(self, srcContext, selection):
        if self.mainFrame.getActiveFit() is None or srcContext != "fittingShip":
            return False

        sFit = Fit.getInstance()
        fitID = self.mainFrame.getActiveFit()
        fit = sFit.getFit(fitID)

        self.modes = fit.ship.modes
        self.currMode = fit.mode

        return srcContext == "fittingShip" and self.modes is not None

    def getText(self, itmContext, selection):
        return "Tactical Mode"

    def addMode(self, menu, mode):
        label = mode.item.name.rsplit()[-2]
        id_ = ContextMenu.nextID()
        self.modeIds[id_] = mode
        menuItem = wx.MenuItem(menu, id_, label, kind=wx.ITEM_RADIO)
        menu.Bind(wx.EVT_MENU, self.handleMode, menuItem)
        return menuItem

    def getSubMenu(self, context, selection, rootMenu, i, pitem):
        msw = True if "wxMSW" in wx.PlatformInfo else False
        self.context = context
        self.modeIds = {}

        sub = wx.Menu()

        for mode in self.modes:
            menuItem = self.addMode(rootMenu if msw else sub, mode)
            sub.AppendItem(menuItem)
            menuItem.Check(self.currMode.item == mode.item)

        return sub

    def handleMode(self, event):
        item = self.modeIds[event.Id]
        if item is False or item not in self.modes:
            event.Skip()
            return

        sFit = Fit.getInstance()
        fitID = self.mainFrame.getActiveFit()
        sFit.setMode(fitID, self.modeIds[event.Id])
        wx.PostEvent(self.mainFrame, GE.FitChanged(fitID=fitID))


TacticalMode.register()
