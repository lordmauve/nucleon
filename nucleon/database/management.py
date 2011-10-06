class SQLScript(object):
    @classmethod
    def open(cls, fname):
        with open(fname) as f:
            commands = f.read()
        return cls(c.strip() + ';' for c in commands.split(';') if c.strip())

    def __init__(self, commands):
        self.commands = commands

    def exec(self, db):
        """Run the SQL script."""
        with db.cursor() as cursor:
            for command in self.commands:
                cursor.execute(command)
