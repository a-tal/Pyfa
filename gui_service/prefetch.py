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

import os
import threading

import config
from eos import db
from eos.db import migration
from eos.db.saveddata.loadDefaultDatabaseValues import DefaultDatabaseValues
from eos.gamedata import getItemsByCategory
from eos.saveddata.character import Character as es_Character


class PrefetchThread(threading.Thread):
    def run(self):
        # TODO: This is awful.  Why would we hide errors? :(
        '''
        # We're a daemon thread, as such, interpreter might get shut down while we do stuff
        # Make sure we don't throw tracebacks to console
        try:
            es_Character.setSkillList(db.getItemsByCategory("Skill", eager=("effects", "attributes", "attributes.info.icon", "attributes.info.unit", "icon")))
        except:
            pass
        '''
        es_Character.setSkillList(getItemsByCategory("Skill"))


prefetch = PrefetchThread()
prefetch.daemon = True
prefetch.start()

# The following code does not belong here, however until we rebuild skeletons
# to include modified pyfa.py, this is the best place to put it. See GH issue
# #176
# @ todo: move this to pyfa.py

# Make sure the saveddata db exists
if config.savePath and not os.path.exists(config.savePath):
    os.mkdir(config.savePath)

if config.saveDB and os.path.isfile(config.saveDB):
    # If database exists, run migration after init'd database
    db.saveddata_meta.create_all()
    migration.update(db.saveddata_engine)
    # Import default database values
    # Import values that must exist otherwise Pyfa breaks
    DefaultDatabaseValues.importRequiredDefaults()
elif config.saveDB:
    # If database does not exist, do not worry about migration. Simply
    # create and set version
    db.saveddata_meta.create_all()
    db.saveddata_engine.execute('PRAGMA user_version = {}'.format(migration.getAppVersion()))
    # Import default database values
    # Import values that must exist otherwise Pyfa breaks
    DefaultDatabaseValues.importRequiredDefaults()
    # Import default values for damage profiles
    DefaultDatabaseValues.importDamageProfileDefaults()
    # Import default values for target resist profiles
    DefaultDatabaseValues.importResistProfileDefaults()
