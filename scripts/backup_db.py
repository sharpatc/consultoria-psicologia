import os
import sqlite3
from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path
from tempfile import gettempdir


def create_backup():
    database_path = os.environ.get('DB_PATH', '/data/database.sqlite')
    backup_path = Path(gettempdir()) / (
        f"consultoria-psicologia-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sqlite3"
    )

    with closing(sqlite3.connect(database_path)) as source:
        with closing(sqlite3.connect(backup_path)) as destination:
            source.backup(destination)

    return backup_path


if __name__ == '__main__':
    print(create_backup())
