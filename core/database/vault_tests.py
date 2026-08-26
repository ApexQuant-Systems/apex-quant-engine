# filename: core/database/vault_tests.py
import unittest
import os
import sqlite3
from core.database.vault import ApexStorageVault

class TestApexVault(unittest.TestCase):
    def setUp(self):
        self.test_db = "data/test_apex_vault.db"
        self.vault = ApexStorageVault(db_path=self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        # Clean up WAL sidecars if generated during testing
        if os.path.exists(self.test_db + "-wal"):
            os.remove(self.test_db + "-wal")
        if os.path.exists(self.test_db + "-shm"):
            os.remove(self.test_db + "-shm")

    def test_sqlite_wal_activation(self):
        conn = sqlite3.connect(self.test_db)
        cursor = conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")
        conn.close()

if __name__ == "__main__":
    unittest.main()
