import subprocess
import sys
from importlib import import_module
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

REQUIREMENTS_FILE = Path(__file__).resolve().parent / "requirements.txt"

def pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

def ensure_dependencies():
    if not REQUIREMENTS_FILE.exists():
        return

    with open(REQUIREMENTS_FILE) as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            # handle pinned versions
            if "==" in line:
                pkg, req_version = line.split("==")
            else:
                pkg, req_version = line, None

            pkg = pkg.strip()

            try:
                import_module(pkg)
                installed = True
            except ImportError:
                installed = False

            if not installed:
                pip_install(line)
                continue

            if req_version:
                try:
                    current = version(pkg)
                    if current != req_version:
                        pip_install(line)
                except PackageNotFoundError:
                    pip_install(line)