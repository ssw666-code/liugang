import sqlite3
import tempfile
import unittest
from pathlib import Path

from smart_daily_system.storage.sqlite import SCHEMA_VERSION, initialize_database


class SqliteStorageTests(unittest.TestCase):
    def test_initialize_database_creates_schema_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "reports.sqlite3"

            initialize_database(database_path)
            initialize_database(database_path)

            connection = sqlite3.connect(database_path)
            try:
                row = connection.execute(
                    "SELECT value FROM schema_meta WHERE key = 'schema_version'"
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(row, (str(SCHEMA_VERSION),))


if __name__ == "__main__":
    unittest.main()
