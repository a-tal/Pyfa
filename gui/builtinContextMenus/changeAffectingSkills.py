# -*- coding: utf-8 -*-
import wx

import gui.globalEvents as GE
import gui.mainFrame
from eos.saveddata.character import Skill as Skill
from gui.bitmapLoader import BitmapLoader
from gui.contextMenu import ContextMenu
from service.character import Character
from service.fit import Fit


class ChangeAffectingSkills(ContextMenu):
    def __init__(self):
        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

    def display(self, srcContext, selection):
        if self.mainFrame.getActiveFit() is None or srcContext not in ("fittingModule", "fittingCharge", "fittingShip"):
            return False

        self.sChar = Character.getInstance()
        self.sFit = Fit.getInstance()
        fit = self.sFit.getFit(self.mainFrame.getActiveFit())

        self.charID = fit.character.ID

        # if self.sChar.getCharName(self.charID) in ("All 0", "All 5"):
        #    return False

        if srcContext == "fittingShip":
            fitID = self.mainFrame.getActiveFit()
            sFit = Fit.getInstance()
            self.stuff = sFit.getFit(fitID).ship
            cont = sFit.getFit(fitID).ship.itemModifiedAttributes
        elif srcContext == "fittingCharge":
            cont = selection[0].chargeModifiedAttributes
        else:
            cont = selection[0].itemModifiedAttributes

        skills = set()

        for attrName in cont.iterAfflictions():
            if cont[attrName] == 0:
                continue

            for fit, afflictors in cont.getAfflictions(attrName).iteritems():
                for afflictor, modifier, amount, used in afflictors:
                    # only add Skills
                    if not isinstance(afflictor, Skill):
                        continue

                    skills.add(afflictor)

        self.skills = sorted(skills, key=lambda x: x.item.name)
        return len(self.skills) > 0

    def getText(self, itmContext, selection):
        return "Change %s Skills" % itmContext

    def addSkill(self, rootMenu, skill, i):
        if i < 0:
            label = "Not Learned"
        else:
            label = "Level %s" % i

        id_ = ContextMenu.nextID()
        self.skillIds[id_] = (skill, i)
        menuItem = wx.MenuItem(rootMenu, id_, label, kind=wx.ITEM_RADIO)
        rootMenu.Bind(wx.EVT_MENU, self.handleSkillChange, menuItem)
        return menuItem

    def getSubMenu(self, context, selection, rootMenu, i, pitem):
        msw = True if "wxMSW" in wx.PlatformInfo else False
        self.skillIds = {}
        sub = wx.Menu()

        for skill in self.skills:
            skillItem = wx.MenuItem(sub, ContextMenu.nextID(), skill.item.name)
            grandSub = wx.Menu()
            skillItem.SetSubMenu(grandSub)
            if skill.learned:
                bitmap = BitmapLoader.getBitmap("lvl%s" % skill.level, "gui")
                if bitmap is not None:
                    skillItem.SetBitmap(bitmap)

            for i in range(-1, 6):
                levelItem = self.addSkill(rootMenu if msw else grandSub, skill, i)
                grandSub.AppendItem(levelItem)
                if (not skill.learned and i == -1) or (skill.learned and skill.level == i):
                    levelItem.Check(True)
            sub.AppendItem(skillItem)

        return sub

    def handleSkillChange(self, event):
        skill, level = self.skillIds[event.Id]

        self.sChar.changeLevel(self.charID, skill.item.ID, level)
        fitID = self.mainFrame.getActiveFit()
        self.sFit.changeChar(fitID, self.charID)

        wx.PostEvent(self.mainFrame, GE.CharListUpdated())
        wx.PostEvent(self.mainFrame, GE.FitChanged(fitID=fitID))


ChangeAffectingSkills.register()
