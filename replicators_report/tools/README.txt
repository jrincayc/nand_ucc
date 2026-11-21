Scripts used to draw the RNDP figures of REPLICATORS_REPORT.md (Python 3 + numpy + Pillow; md2html.py needs python-markdown).
render.py     reads rndp build files, rndp-state files, or the R5 command pickle; writes SVG windows or PNG overviews.
make_figs.py  draws every fig_*.svg from the rebuilt worlds (see its docstring and report Appendix B for how each world was rebuilt).
md2html.py    renders the report to HTML; --embed inlines the SVG figures so the page is self-contained.
The y_*.svg figures are copies of y/writeup/figs/.
md2pdf.py     two-column Letter PDF via headless Chromium (playwright): python3 tools/md2pdf.py REPLICATORS_REPORT.md OUT.pdf
