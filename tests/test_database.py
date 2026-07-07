import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import database


class InitDbFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = self.temp_db.name

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_init_db_falls_back_to_local_sqlite_when_remote_connect_fails(self):
        with patch("database.get_connection", side_effect=RuntimeError("remote unavailable")):
            database.init_db()

        conn = sqlite3.connect(self.temp_db.name)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            self.assertIsNotNone(cursor.fetchone())
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
