"""Durable JSON records, hash-linked journal, and exclusive process ownership.

Requires a local filesystem with working OS locks and SQLite durability.
No network-filesystem or hostile-administrator guarantees are asserted.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading

from .contracts import Refused, digest, encode


class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mutex = threading.RLock()
        self.closed = False
        self.lock = open(str(self.path) + ".lock", "a+b")
        self.lock.seek(0, os.SEEK_END)
        if self.lock.tell() == 0:
            self.lock.write(b"0")
            self.lock.flush()
        self.lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.lock.close()
            raise Refused("authority database already has an owner") from exc
        try:
            self.db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
            self.db.execute("PRAGMA journal_mode=DELETE")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA busy_timeout=2000")
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise Refused("database integrity failure")
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise Refused("unsupported storage schema")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                    checksum TEXT NOT NULL, PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY, body TEXT NOT NULL,
                    previous TEXT NOT NULL, checksum TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
            self.verify()
        except BaseException:
            self.close()
            raise

    @contextmanager
    def transaction(self):
        with self.mutex:
            if self.closed:
                raise Refused("runtime is closed")
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise

    def get(self, kind, key):
        with self.mutex:
            row = self.db.execute("SELECT body,checksum FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
            if row is None:
                raise Refused(f"unknown {kind} reference")
            if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                raise Refused("record checksum mismatch")
            return json.loads(row[0])

    def find(self, kind):
        with self.mutex:
            ids = [r[0] for r in self.db.execute("SELECT id FROM records WHERE kind=? ORDER BY id", (kind,))]
            return [self.get(kind, key) for key in ids]

    def put(self, kind, key, value):
        if not self.db.in_transaction:
            raise RuntimeError("writes require an explicit transaction")
        body = encode(value)
        self.db.execute("INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,checksum=excluded.checksum",
                        (kind, key, body, hashlib.sha256(body.encode()).hexdigest()))

    def event(self, kind, **fields):
        if not self.db.in_transaction:
            raise RuntimeError("journal writes require an explicit transaction")
        previous = self.db.execute("SELECT checksum FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous = previous[0] if previous else "0" * 64
        body = encode({"kind": kind, **fields})
        checksum = digest([previous, body])
        self.db.execute("INSERT INTO events(body,previous,checksum) VALUES (?,?,?)", (body, previous, checksum))

    def journal(self):
        with self.mutex:
            return [dict(seq=row[0], **json.loads(row[1])) for row in self.db.execute("SELECT seq,body FROM events ORDER BY seq")]

    def verify(self):
        previous = "0" * 64
        for body, parent, checksum in self.db.execute("SELECT body,previous,checksum FROM events ORDER BY seq"):
            if parent != previous or digest([parent, body]) != checksum:
                raise Refused("journal integrity failure")
            previous = checksum
        for kind, key in self.db.execute("SELECT kind,id FROM records"):
            self.get(kind, key)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if hasattr(self, "db"):
            self.db.close()
        if not self.lock.closed:
            self.lock.close()  # process locks are released by closing the handle
