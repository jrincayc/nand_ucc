#!/usr/bin/env python3
"""md2pdf.py REPORT.md OUT.pdf -- two-column print layout of the report, rendered with headless Chromium (playwright).
Figures and tables with 6 or more columns span both columns; everything else flows in two columns."""
import sys, os, re, base64, asyncio, markdown

src, out = sys.argv[1], sys.argv[2]
base = os.path.dirname(os.path.abspath(src))
md = open(src, encoding='utf-8').read()
title = re.search(r'^# (.+)$', md, re.M).group(1)
md = re.sub(r'^# .+\n', '', md, count=1)                     # title goes in a custom header block
body = markdown.markdown(md, extensions=['tables', 'sane_lists'])


def svg_uri(m):
    data = open(os.path.join(base, m.group(1)), 'rb').read()
    return 'src="data:image/svg+xml;base64,' + base64.b64encode(data).decode() + '"'


body = re.sub(r'src="(figs/[^"]+\.svg)"', svg_uri, body)
body = re.sub(r'<p>((?:<img[^>]*>\s*)+)</p>\s*<p><em>(Figure.*?)</em></p>',
              r'<figure>\1<figcaption>\2</figcaption></figure>', body, flags=re.S)


def table_cls(m):
    t = m.group(0)
    head = re.search(r'<tr>(.*?)</tr>', t, re.S).group(1)
    ncol = head.count('<th')
    return t.replace('<table>', '<table class="wide">' if ncol >= 5 else '<table>', 1)


body = re.sub(r'<table>.*?</table>', table_cls, body, flags=re.S)
# the intro paragraph (italic lines before the first <hr>) becomes the abstract-style subtitle
first_hr = body.find('<hr')
intro, rest = body[:first_hr], body[first_hr:]
rest = re.sub(r'<hr\s*/?>', '', rest)
# small figures (gate graphs) side by side get a class
body = rest

css = """
@page { size: Letter; margin: 0.65in 0.6in 0.7in 0.6in; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; color: #161616; font: 9.4pt/1.42 'Georgia', 'Times New Roman', serif; }
.titleblock { column-span: all; border-bottom: 1.2pt solid #222; padding-bottom: 10pt; margin-bottom: 12pt; }
.titleblock h1 { font: bold 20pt/1.2 Helvetica, Arial, sans-serif; margin: 0 0 6pt; }
.titleblock p { margin: 2pt 0; font-size: 9.6pt; color: #444; }
.cols { column-count: 2; column-gap: 0.3in; column-fill: balance; }
h2 { font: bold 12.5pt/1.25 Helvetica, Arial, sans-serif; margin: 14pt 0 5pt; break-after: avoid; }
h3 { font: bold 10.2pt/1.3 Helvetica, Arial, sans-serif; margin: 10pt 0 4pt; break-after: avoid; }
p { margin: 0 0 5.5pt; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 6pt; padding-left: 14pt; }
li { margin: 0 0 2pt; text-align: left; }
li > ul, li > ol { margin-top: 2pt; }
a { color: #1d5fae; text-decoration: none; }
code { font: 8.2pt Menlo, Consolas, monospace; background: #f3f2ee; padding: 0 2pt; border-radius: 2pt; }
strong { font-weight: bold; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 9pt; font: 7.4pt/1.3 Helvetica, Arial, sans-serif; break-inside: avoid; }
table.wide { column-span: all; font-size: 7.2pt; margin: 6pt 0 12pt; }
th, td { border-bottom: 0.5pt solid #d6d3cb; padding: 2.2pt 3.5pt; text-align: left; vertical-align: top; }
th { background: #f1f0eb; border-bottom: 0.9pt solid #999; font-weight: bold; }
td { font-variant-numeric: tabular-nums; }
figure { column-span: all; margin: 8pt 0 12pt; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 4.3in; height: auto; display: inline-block; vertical-align: top; }
figure.pair img { max-width: 48%; }
figcaption { font: 8pt/1.35 Helvetica, Arial, sans-serif; color: #444; text-align: left; margin-top: 4pt; }
"""
# the full-adder pair: two images in one figure
body = body.replace('<figure><img alt="Figure 4a"', '<figure class="pair"><img alt="Figure 4a"')
intro_html = re.sub(r'</?p>', '', intro).strip()
html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{css}</style></head>
<body><div class="cols"><div class="titleblock"><h1>{title}</h1><p>{intro_html}</p></div>
{body}
</div></body></html>"""
tmp = os.path.splitext(out)[0] + '_print.html'
open(tmp, 'w', encoding='utf-8').write(html)


async def render():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        await pg.goto('file://' + os.path.abspath(tmp))
        await pg.wait_for_timeout(2000)
        foot = ("<div style='width:100%;font:7.5pt Helvetica,Arial,sans-serif;color:#777;padding:0 0.6in;display:flex;justify-content:space-between'>"
                f"<span>{title}</span><span><span class='pageNumber'></span> / <span class='totalPages'></span></span></div>")
        await pg.pdf(path=out, format='Letter', print_background=True, display_header_footer=True,
                     header_template='<div></div>', footer_template=foot,
                     margin={'top': '0.6in', 'bottom': '0.7in', 'left': '0.6in', 'right': '0.6in'})
        await b.close()

asyncio.run(render())
print(out, os.path.getsize(out) // 1024, 'KiB')
