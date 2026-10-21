"""Create a local side-by-side visual review document without modifying original references."""
from pathlib import Path
from urllib.parse import quote
from html import escape

root = Path(__file__).resolve().parents[1]
names = ['01-sign-in', '02-home', '03-discuss', '04-videos', '05-toolkit', '06-updates', '07-publications', '08-reminders', '09-alerts']
references = sorted((root.parent / 'targetUI').glob('*.png'))
cards = []
for reference, name in zip(references, names):
    cards.append(f'<section><h2>{escape(reference.stem)}</h2><div class="pair"><figure><figcaption>Approved reference</figcaption><img src="../../targetUI/{quote(reference.name)}"></figure><figure><figcaption>Flutter widget capture · demonstration fixtures</figcaption><img src="screenshots/{name}.png"></figure></div></section>')
html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>DSBCA visual reference review</title><style>body{font:15px system-ui;background:#f6f3fc;color:#24212d;margin:0;padding:32px}main{max-width:1000px;margin:auto}h1{font-family:Georgia}h2{margin-top:48px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}figure{margin:0}figcaption{margin:0 0 12px;color:#827c90}img{width:100%;max-width:390px;border:1px solid #e4ddf4;border-radius:20px;display:block}p{max-width:760px;line-height:1.6}@media(max-width:600px){body{padding:16px}.pair{gap:8px}figcaption{font-size:11px}}</style><main><h1>DSBCA visual reference review</h1><p>Original images are preserved. Implemented captures are real Flutter widgets at 390 × 844 using isolated demonstration fixtures. They verify layout, not live database contents. Responsive tests cover all six requested widths. Differences for demonstration labels, legal-copy handling, authentication and functional CRUD controls are intentional; visual sign-off remains a human review.</p>'''
(root / 'docs/UI_COMPARISON.html').write_text(html + ''.join(cards) + '</main></html>', encoding='utf-8')
print('Created docs/UI_COMPARISON.html')
