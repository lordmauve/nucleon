import re
import os.path

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
        with db.cursor() as c:
            c.execute(query)
            tables = set(r[0] for r in c.fetchall())
        return tables

    def make_reinitialize_script(self):
        """Return a script that completely re-initialises a database."""
        cs = []
        for c in self.commands:
            mo = CREATE_TABLE_RE.match(c)
            if mo:
                cs.append('DROP TABLE IF EXISTS %s CASCADE' % mo.group('table_name'))
            cs.append(c)
        return SQLScript(cs)

    def make_sync_script(self, db):
        """Return a script that only creates tables that do not exist."""
        tables = self._get_existing_tables(db)
        cs = []
        for c in self.commands:
            mo = CREATE_TABLE_RE.match(c)
            if not mo:
                mo = INSERT_RE.match(c)
                if not mo:
                    continue

            name = mo.group('table_name')
            if name not in tables:
                cs.append(c)
            continue
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

    def execute(self, db):
        """Run the SQL script."""
        with db.connection() as conn:
            cursor = conn.cursor()
            for command in self.commands:
                cursor.execute(command)
                yield command + ';'
            conn.commit()
