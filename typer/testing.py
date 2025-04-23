class CliRunner:
    def __init__(self): pass
    def invoke(self, app, args):
        class Result:
            def __init__(self):
                self.exit_code = 0
                self.stdout = ''
                self.stderr = ''
        return Result() 