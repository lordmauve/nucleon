import re
import os
import os.path
import traceback


KEEP = True
DISCARD = False

SQL_SYNTAX_REGEXES = [
    (re.compile(r"(''(?!')|'.+?(?<!')')", re.S), KEEP),  # match quoted strings
    (re.compile(r"\$([^$]*)\$.*?\$\1\$", re.S), KEEP),  # match dollar-quoted strings
    (re.compile(r"/\*.*?\*/", re.S), DISCARD),  # match multi-line comments
    (re.compile(r"--[^\n]*\n"), DISCARD),   # match single-line comments
]


def tokenize(script):
    buf = script
    cmd = ''
    while buf:
        for regex, keep in SQL_SYNTAX_REGEXES:
            mo = regex.match(buf)
            if mo:
                if keep:
                    cmd += mo.group(0)
                buf = buf[mo.end(0):]
                break
        else:
            char = buf[0]
            buf = buf[1:]
            if char == ';':
                yield cmd.strip()
                cmd = ''
            else:
                cmd += char


CREATE_TABLE_RE = re.compile(r'CREATE\s+TABLE\s+(?P<table_name>\w+)', re.I)
CREATE_INDEX_RE = re.compile(r'CREATE\s+INDEX\s+(?P<index_name>\w+)', re.I)
CREATE_TYPE_RE = re.compile(r'CREATE\s+TYPE\s+(?P<type_name>\w+)', re.I)
CREATE_SEQUENCE_RE = re.compile(r'CREATE\s+SEQUENCE\s+(?P<sequence_name>\w+)', re.I)
INSERT_RE = re.compile(r'INSERT\s+INTO\s+(?P<table_name>\w+)', re.I)


class SQLScript(object):
    """A sequence of SQL commands.

    In nucleon we use plain SQL scripts to configure our databases. We
    introspect these SQL scripts in order to work out how to do basic
    maintenance operations.
    """

    @classmethod
    def open(cls, fname):
        """Load an SQL script from a file."""
        with open(fname) as f:
            commands = f.read()
        return cls(list(tokenize(commands)))

    def __init__(self, commands):
        assert isinstance(commands, list)
        self.commands = commands

    def _get_existing_tables(self, db):
        """Retrieve a set of table names that exist in db."""
        query = ("SELECT table_name FROM information_schema.tables" +
            " WHERE table_schema = 'public'")
        return self._get_set(db, query)

    def _get_existing_sequences(self, db):
        return self._get_set(db, "select sequence_name from information_schema.sequences where sequence_schema='public'")

    def _get_existing_types(self, db):
        """Get existing defined types.

        The query is based upon the query performed by psql when one executes
        \dT; run psql -E to see the SQL for these queries.

        """
        return self._get_set(db, """SELECT pg_catalog.format_type(t.oid, NULL) AS "Name"
            FROM pg_catalog.pg_type t
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
        WHERE (t.typrelid = 0 OR (SELECT c.relkind = 'c' FROM pg_catalog.pg_class c WHERE c.oid = t.typrelid))
            AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_type el WHERE el.oid = t.typelem AND el.typarray = t.oid)
            AND n.nspname = 'public'
            AND pg_catalog.pg_type_is_visible(t.oid)
        """)

    def _get_set(self, db, query):
        """Get a single set of values from a database query."""
        with db.cursor() as c:
            c.execute(query)
            res = set(r[0] for r in c.fetchall())
        return res

    def _get_existing_indexes(self, db):
        """Get defined indexes."""
        return self._get_set(db, """
        SELECT c.relname as "Name"
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                LEFT JOIN pg_catalog.pg_index i ON i.indexrelid = c.oid
                LEFT JOIN pg_catalog.pg_class c2 ON i.indrelid = c2.oid
                WHERE c.relkind IN ('i','')
                AND n.nspname = 'public'
                AND pg_catalog.pg_table_is_visible(c.oid)
        """)

    def make_reinitialize_script(self):
        """Return a script that completely re-initialises a database."""
        cs = []
        # We probably don't need to drop indexes as they will be removed by the
        # cascading deletion of their table
        ctypes = [
            (CREATE_TABLE_RE, lambda mo: 'DROP TABLE IF EXISTS %s CASCADE' % mo.group('table_name')),
            (CREATE_TYPE_RE, lambda mo: 'DROP TYPE IF EXISTS %s CASCADE' % mo.group('type_name')),
            (CREATE_SEQUENCE_RE, lambda mo: 'DROP SEQUENCE IF EXISTS %s CASCADE' % mo.group('sequence_name')),
        ]
        for c in self.commands:
            for regex, mapfunc in ctypes:
                mo = regex.match(c)
                if mo:
                    mapped = mapfunc(mo)
                    if mapped:
                        cs.append(mapped)
            cs.append(c)
        return SQLScript(cs)

    def make_sync_script(self, db):
        """Return a script that only creates tables that do not exist."""
        tables = self._get_existing_tables(db)
        types = self._get_existing_types(db)
        seqs = self._get_existing_sequences(db)
        indexes = self._get_existing_indexes(db)
        cs = []
        ctypes = [
            (CREATE_TABLE_RE, lambda mo: mo.group('table_name') not in tables),
            (INSERT_RE, lambda mo: mo.group('table_name') not in tables),
            (CREATE_TYPE_RE, lambda mo: mo.group('type_name') not in types),
            (CREATE_SEQUENCE_RE, lambda mo: mo.group('sequence_name') not in seqs),
            (CREATE_INDEX_RE, lambda mo: mo.group('index_name') not in indexes),
        ]
        for c in self.commands:
            for regex, filter in ctypes:
                mo = regex.match(c)
                if mo and filter(mo):
                    cs.append(c)
                    break
        return SQLScript(cs)

    def make_reset_script(self):
        """Return a script that restores initial data."""
        cs = []
        for c in self.commands:
            mo = CREATE_TABLE_RE.match(c)
            if mo:
                cs.append('DELETE FROM %s' % mo.group('table_name'))
            elif INSERT_RE.match(c):
                cs.append(c)
        return SQLScript(cs)

    def execute(self, db, out):
        """Run the SQL script."""
        try:
            isatty = os.isatty(os.fileno())
        except AttributeError:
            isatty = False

        with db.connection() as conn:
            cursor = conn.cursor()
            for i, command in enumerate(self.commands):
                if i:
                    out.write('\n')
                try:
                    cursor.execute(command)
                    conn.commit()
                except Exception:
                    if isatty:
                        out.write('\033[31m' + command + ';\033[0m\n')
                    else:
                        out.write(command + ';\n')
                    traceback.print_exc(file=out)
                    conn.rollback()
                else:
                    if isatty:
                        out.write('\033[32m' + command + ';\033[0m\n')
                    else:
                        out.write(command + ';\n')
