import traceback


def try_import(import_func, *, label="UNKNOWN"):
    try:
        return import_func()
    except Exception:
        print(f"\n[⚠️ IMPORT DEBUG - {label}] Import failed:\n")
        traceback.print_exc()
        raise
