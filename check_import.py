import traceback
import sys
try:
    from steam.core.cm import CMClient
    print("OK")
except Exception:
    traceback.print_exc()
