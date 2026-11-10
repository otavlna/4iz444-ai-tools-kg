<!--
Front matter of the report. Each "## key" section is inserted into the corresponding place
of the FIS template (report/template/fis-template.docx) by scripts/build_docx.py.
Lines starting with "- " are rendered as bullet points.
-->

## university
Prague University of Economics and Business

## faculty
Faculty of Informatics and Statistics

## title
AI Tools Catalogue: A Knowledge Graph of AI Tools, Models and Providers

## type
SEMESTRAL PROJECT

## course
Course: 4IZ444

## authors
Authors: Ota Vlna, Matěj Fadrhons

## place-date
Prague, December 2026

## ai-heading
Declaration on the Use of Artificial Intelligence

## ai-intro
We confirm that artificial intelligence tools **were used** in the preparation of this work, specifically in the following ways:

## ai-uses
- improving grammar and language style,
- editing and extending parts of the text,
- generating parts of the source code (ontology, SPARQL queries, SHACL shapes and build scripts),
- generating data,
- other: drafting the text of the report.

## ai-note
Each use is documented separately in Appendix B, which explains in more detail which tool was used in which part of the work and highlights our own contribution.

## ai-confirm
We confirm that:

## ai-confirm-items
- our work is original and was prepared in accordance with ethical standards, in particular with the Code of Ethics of the Prague University of Economics and Business, all information sources used are cited and the generated content was verified by us;
- we accept full responsibility for the entire content of the work.

## abstract-cs-heading
Abstrakt

## abstract-cs
Práce se zabývá návrhem a vytvořením znalostního grafu, který popisuje katalog nástrojů umělé inteligence – produkty jako ChatGPT, Claude, Gemini, Midjourney nebo GitHub Copilot, modely, na kterých tyto nástroje běží, jejich poskytovatele, podporované úlohy, vstupní a výstupní modality, licence, integrace, cenové plány a výsledky benchmarků. Znalostní graf má sloužit jako podpora při výběru AI nástroje pro vývojáře, IT oddělení a analytiky trhu.

Na základě deseti kompetenčních otázek byla navržena ontologie v jazyce OWL 2 s 13 třídami, 25 vlastnostmi a axiomy (hierarchie tříd, disjunktnost, funkční, inverzní, tranzitivní a symetrické vlastnosti). Ontologie odděluje nástroj od modelu a modeluje výsledky benchmarků jako n-ární vztah. Termíny byly sladěny s existujícími slovníky schema.org, W3C ML Schema, Dublin Core, FOAF a SKOS. Ontologie byla naplněna daty o 15 nástrojích, 27 modelech a 12 poskytovatelích (téměř 1 000 trojic), kompetenční otázky a pět dalších analytických dotazů byly převedeny do jazyka SPARQL a kvalita dat je kontrolována jedenácti tvary SHACL. Výsledky ukazují například silnou koncentraci trhu na úrovni modelů – nástroje třetích stran stojí převážně na modelech tří poskytovatelů.

## keywords-cs-heading
Klíčová slova

## keywords-cs
znalostní graf, ontologie, OWL, SPARQL, SHACL, umělá inteligence, jazykové modely

## abstract-en-heading
Abstract

## abstract-en
This work designs and builds a knowledge graph describing a catalogue of artificial intelligence tools – products such as ChatGPT, Claude, Gemini, Midjourney or GitHub Copilot – together with the models that power them, their providers, supported tasks, input and output modalities, licences, integrations, pricing plans and benchmark results. The knowledge graph is intended to support the selection of AI tools by developers, IT departments and market analysts.

Based on ten competency questions, an OWL 2 ontology with 13 classes, 25 properties and a range of axioms (class hierarchy, disjointness, functional, inverse, transitive and symmetric properties) was designed. The ontology separates tools from models and represents benchmark results as an n-ary relation; its terms are aligned with the existing vocabularies schema.org, W3C ML Schema, Dublin Core, FOAF and SKOS. The ontology was populated with data on 15 tools, 27 models and 12 providers (almost 1,000 triples), the competency questions and five additional analytical queries were translated into SPARQL, and data quality is checked by eleven SHACL shapes. The results show, for example, a strong concentration of the market at the model level – third-party tools rely mostly on the models of three providers.

## keywords-en-heading
Keywords

## keywords-en
knowledge graph, ontology, OWL, SPARQL, SHACL, artificial intelligence, language models

## toc-heading
Contents
