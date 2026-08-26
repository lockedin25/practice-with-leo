#!/usr/bin/env bash
#
# Copy the production database off the machine that holds it.
#
# The volume is a single disk with no redundancy. It carries every account,
# transcript, evaluation and debrief, and none of that is reconstructible: the
# case content is in git, the record of people using it is not.
#
# Uses SQLite's own .backup rather than `cp`. Under WAL a plain copy of the
# database file taken mid-write yields a file missing whatever is still in the
# -wal sidecar, which restores as a database that is subtly short rather than
# obviously broken. .backup takes a consistent snapshot of a live database.
#
#   ./scripts/backup_db.sh                 # into ./backups
#   ./scripts/backup_db.sh /path/to/dir    # somewhere else
#
# To run it against the deployed machine:
#   fly ssh console --app leo-case-prep -C \
#     "python -c \"import sqlite3;s=sqlite3.connect('/data/casecall.db');d=sqlite3.connect('/tmp/backup.db');s.backup(d);d.close()\""
#   fly ssh sftp get /tmp/backup.db ./backups/casecall-$(date +%F).db --app leo-case-prep

set -euo pipefail

DB="${DATABASE_PATH:-data/casecall.db}"
DEST="${1:-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${DEST}/casecall-${STAMP}.db"

if [ ! -f "$DB" ]; then
  echo "No database at ${DB}" >&2
  exit 1
fi

mkdir -p "$DEST"

python3 - "$DB" "$OUT" <<'PY'
import sqlite3, sys
source, destination = sys.argv[1], sys.argv[2]
src = sqlite3.connect(source)
dst = sqlite3.connect(destination)
with dst:
    src.backup(dst)
# Verify before claiming success. A backup nobody has restored is a guess, and
# integrity_check is the cheapest possible version of actually restoring it.
result = dst.execute("PRAGMA integrity_check").fetchone()[0]
counts = {
    table: dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    for table in ("users", "attempts", "evaluations")
}
dst.close(); src.close()
if result != "ok":
    sys.exit(f"Backup failed integrity check: {result}")
print(f"integrity: {result}   " + "  ".join(f"{k}={v}" for k, v in counts.items()))
PY

echo "Wrote ${OUT} ($(du -h "$OUT" | cut -f1))"

# Keep the last 14. Older than that and either the problem was noticed long ago
# or the data is stale enough not to want.
ls -1t "${DEST}"/casecall-*.db 2>/dev/null | tail -n +15 | while read -r old; do
  rm -f "$old"
  echo "Pruned ${old}"
done
