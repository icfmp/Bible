"""Native-allocation tracing wrapper; a diagnostic dependency, not app code."""
import os
import memray
from tools.profile_alpha_performance import main

if __name__=='__main__':
    with memray.Tracker(os.environ['ALPHA_NATIVE_TRACE'],native_traces=True,trace_python_allocators=True):
        main()
