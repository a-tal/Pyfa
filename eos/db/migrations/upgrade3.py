"""
Migration 3

- Adds mode column for fits (t3 dessy)
"""

from sqlalchemy import exc as sqlalchemy_exc


def upgrade(saveddata_engine):
    try:
        saveddata_engine.execute("SELECT modeID FROM fits LIMIT 1")
    except sqlalchemy_exc.DatabaseError:
        saveddata_engine.execute("ALTER TABLE fits ADD COLUMN modeID INTEGER")
