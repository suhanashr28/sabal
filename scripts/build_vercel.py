"""Publish only public styles/scripts; pages and media remain authenticated."""
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'public'
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)
OUTPUT.mkdir()
for folder in [ROOT, ROOT / 'play']:
    for source in folder.iterdir():
        if source.is_file() and source.suffix in {'.css', '.js'}:
            target = OUTPUT / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
shutil.copyfile(ROOT / 'login.html', OUTPUT / 'login.html')
