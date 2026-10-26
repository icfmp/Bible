"""Native-allocation tracing wrapper; a diagnostic dependency, not app code."""
import os
import memray
from functools import partial
from tests import test_ui

# Native tracing heavily amplifies cold layout/metadata work. Wait for the
# same readiness condition; ordinary performance runs keep their normal limit.
test_ui.spin=partial(test_ui.spin,timeout=120)
from tools.profile_alpha_performance import main

if __name__=='__main__':
    with memray.Tracker(os.environ['ALPHA_NATIVE_TRACE'],native_traces=True,trace_python_allocators=True):
        main()
