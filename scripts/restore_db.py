import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path


def restore_database(backup_path):
    database_path = Path(os.environ.get('DB_PATH', '/data/database.sqlite'))
    backup_path = Path(backup_path).resolve(strict=True)
    temporary_path = database_path.with_name('database.restore.sqlite')

    with closing(sqlite3.connect(f'{backup_path.as_uri()}?mode=ro', uri=True)) as source:
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('La copia de seguridad no paso la verificacion de integridad.')
        tables = {
            row[0] for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not {'users', 'messages'}.issubset(tables):
            raise RuntimeError('El archivo no contiene una base de datos valida de la aplicacion.')

        with closing(sqlite3.connect(temporary_path)) as destination:
            source.backup(destination)

    for suffix in ('-wal', '-shm'):
        database_path.with_name(database_path.name + suffix).unlink(missing_ok=True)
    os.replace(temporary_path, database_path)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python scripts/restore_db.py /ruta/a/copia.sqlite3')
    restore_database(sys.argv[1])
