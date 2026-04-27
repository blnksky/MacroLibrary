try:
    import subprocess
    import sys
    from importlib import import_module
    from importlib.metadata import version, PackageNotFoundError
    from pathlib import Path

    REQUIREMENTS_FILE = Path(__file__).resolve().parent / "requirements.txt"

    def pip_install(pkg):
        print(f"[pip] Installing {pkg}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[pip] Failed to install {pkg}")
            print(result.stderr)

    def ensure_dependencies():
        if not REQUIREMENTS_FILE.exists():
            print("No requirements.txt found.")
            return

        with open(REQUIREMENTS_FILE) as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "==" in line:
                    pkg, req_version = line.split("==")
                else:
                    pkg, req_version = line, None

                pkg = pkg.strip()

                # safer import check
                try:
                    import_module(pkg)
                except ImportError:
                    pip_install(line)
                    continue

                if req_version:
                    try:
                        current = version(pkg)
                        if current != req_version:
                            pip_install(line)
                    except PackageNotFoundError:
                        pip_install(line)

    ensure_dependencies()
except: input(); raise