# Stub of streamlit for testing purposes

class _Container:
    def __init__(self): pass
    def container(self): return self
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass


def set_page_config(*args, **kwargs): pass

def title(*args, **kwargs): pass

def caption(*args, **kwargs): pass

def empty(): return _Container()

def subheader(*args, **kwargs): pass

def dataframe(*args, **kwargs): pass

def info(*args, **kwargs): pass

def error(*args, **kwargs): pass 
