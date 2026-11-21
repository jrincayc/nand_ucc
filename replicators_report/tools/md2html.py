#!/usr/bin/env python3
"""md2html.py REPORT.md OUT.html [--embed] -- render the report as one HTML page.
With --embed every figs/*.svg is inlined as a data URI, so the page is self-contained."""
import sys, os, re, base64, markdown

src, out = sys.argv[1], sys.argv[2]
embed = '--embed' in sys.argv
base = os.path.dirname(os.path.abspath(src))
md = open(src, encoding='utf-8').read()
title = re.search(r'^# (.+)$', md, re.M).group(1)
body = markdown.markdown(md, extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])


def fig(m):
    path = m.group(1)
    if embed:
        data = open(os.path.join(base, path), 'rb').read()
        path = 'data:image/svg+xml;base64,' + base64.b64encode(data).decode()
    return f'src="{path}"'


body = re.sub(r'src="(figs/[^"]+\.svg)"', fig, body)
# a paragraph that is only images, followed by an italic caption paragraph -> figure
body = re.sub(r'<p>((?:<img[^>]*>\s*)+)</p>\s*<p><em>(Figure[^<]*(?:<[^/][^>]*>[^<]*</[^>]+>[^<]*)*)</em></p>',
              r'<figure>\1<figcaption>\2</figcaption></figure>', body)
css = """
:root{--ink:#1b1b1a;--ink2:#52514e;--rule:#e2e0da;--bg:#fff;--soft:#f6f5f1;--accent:#2a78d6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Georgia,'Iowan Old Style','Palatino Linotype',serif}
main{max-width:980px;margin:0 auto;padding:40px 28px 80px}
h1,h2,h3{font-family:Helvetica,Arial,sans-serif;line-height:1.25;color:var(--ink)}
h1{font-size:2.0em;margin:.2em 0 .4em}
h2{font-size:1.45em;margin-top:2.2em;padding-top:.6em;border-top:1px solid var(--rule)}
h3{font-size:1.12em;margin-top:1.6em}
p,li{max-width:46em}
a{color:var(--accent)}
code{font-family:Menlo,Consolas,monospace;font-size:.86em;background:var(--soft);padding:.05em .3em;border-radius:3px}
hr{border:0;border-top:1px solid var(--rule);margin:2em 0}
table{border-collapse:collapse;margin:1.2em 0;font:13.5px/1.4 Helvetica,Arial,sans-serif;display:block;overflow-x:auto;max-width:100%}
th,td{border-bottom:1px solid var(--rule);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--soft);font-weight:600;border-bottom:2px solid #cfccc4}
td{font-variant-numeric:tabular-nums}
figure{margin:1.6em 0;padding:0}
figure img{display:block;max-width:100%;height:auto;margin:0 auto 8px;border:1px solid var(--rule);border-radius:4px;background:#fff}
figcaption{font:13.5px/1.45 Helvetica,Arial,sans-serif;color:var(--ink2);max-width:52em}
img{max-width:100%;height:auto}
.toc{font:14px/1.5 Helvetica,Arial,sans-serif;background:var(--soft);padding:12px 20px;border-radius:6px;margin:1.5em 0}
.toc ul{margin:.2em 0;padding-left:1.2em}
@media print{main{max-width:none;padding:0}h2{break-before:auto}figure{break-inside:avoid}}
"""
toc = markdown.Markdown(extensions=['toc'])
toc.convert(md)
toc_html = toc.toc.replace('<div class="toc">', '<nav class="toc"><strong>Contents</strong>').replace('</div>', '</nav>')
# drop the h1 entry level from the toc: keep only h2 items
body = body.replace('<hr />', '<hr>', 1)
first_hr = body.find('<hr>')
body = body[:first_hr] + toc_html + body[first_hr:] if first_hr > 0 else toc_html + body
html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{css}</style></head>
<body><main>
{body}
</main></body></html>"""
open(out, 'w', encoding='utf-8').write(html)
print(out, len(html) // 1024, 'KiB')
