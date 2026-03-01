"""
Python entrypoint — sets env vars and execs the application.

Using Python instead of shell `exec env` because os.execvp reliably
inherits os.environ, whereas shell variable scoping is unreliable
when bridging across process boundaries.
"""
import os
import sys

# Bridge: if filaops_pro is installed, set the generic plugin module var
# so Core's load_plugin finds it without knowing about PRO specifically.
if os.getenv("FILAOPS_LICENSE_KEY"):
    try:
        import filaops_pro  # noqa: F401
        os.environ["FILAOPS_PRO_MODULE"] = "filaops_pro"
    except ImportError:
        pass  # Not installed — Community mode

# Run the given command or default to uvicorn
if len(sys.argv) > 1:
    cmd = sys.argv[1:]
    os.execvp(cmd[0], cmd)
else:
    os.execvp("uvicorn", [
        "uvicorn", "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
    ])
