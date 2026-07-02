"""Entry-point para o empacotamento PyInstaller (.app autocontido).

Em desenvolvimento continue usando ``python -m app.main`` / ``./run.sh``;
este wrapper existe porque o PyInstaller empacota a partir de um script.
"""

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
