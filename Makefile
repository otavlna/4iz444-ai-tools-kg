PYTHON ?= .venv/bin/python
ZIP     = build/4iz444-ai-tools-kg.zip

.PHONY: all venv build docx pdf zip clean

all: pdf

venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# parse + reason + queries + SHACL + diagram + build/report.md
build:
	$(PYTHON) scripts/build.py

# build/report.md -> report/report.docx (FIS template)
docx: build
	$(PYTHON) scripts/build_docx.py

# report/report.docx -> report/report.pdf (LibreOffice, table of contents filled in)
pdf: docx
	$(PYTHON) scripts/make_pdf.py

# archive for submission in InSIS: PDF + ontology + data + SPARQL + SHACL
zip: pdf
	rm -f $(ZIP)
	zip -r $(ZIP) report/report.pdf ontology data queries shacl results README.md

clean:
	rm -rf build results report/figures report/report.pdf report/report.docx
