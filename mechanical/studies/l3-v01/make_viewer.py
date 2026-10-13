from pathlib import Path
p=Path(__file__).resolve().parent
(p/'viewer.html').write_text((p/'viewer_template.html').read_text().replace('__MESHES__',(p/'meshes.json').read_text()))
