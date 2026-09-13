"""Never publish repository files or private media as unprotected static assets."""
from pathlib import Path
Path('public').mkdir(exist_ok=True)
Path('public/.gitkeep').touch()
