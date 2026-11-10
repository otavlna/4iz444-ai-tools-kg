PYTHON ?= .venv/bin/python
CHROME ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
ZIP     = build/4iz444-ai-tools-kg.zip

.PHONY: all venv build report pdf zip clean

all: pdf

venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# parse + reason + queries + SHACL + diagram + build/report.md
build:
	$(PYTHON) scripts/build.py

build/report.html: build report/report.md report/style.css
	pandoc build/report.md -o build/report.html --standalone --toc --toc-depth=2 \
		--resource-path=report --embed-resources --css=report/style.css \
		--syntax-highlighting=tango --metadata title-prefix=""

report/report.pdf: build/report.html
	"$(CHROME)" --headless=new --disable-gpu --no-pdf-header-footer \
		--print-to-pdf=report/report.pdf build/report.html 2>/dev/null

pdf: report/report.pdf

# archive for submission in InSIS: PDF + ontology + data + SPARQL + SHACL
zip: pdf
	rm -f $(ZIP)
	zip -r $(ZIP) report/report.pdf ontology data queries shacl results README.md

clean:
	rm -rf build results report/figures report/report.pdf
