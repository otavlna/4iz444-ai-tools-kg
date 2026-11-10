<!--
Main text of the report. It is assembled by scripts/build.py (placeholders are replaced by
generated content, captions are numbered per chapter) and converted into the FIS Word template
by scripts/build_docx.py. Front matter (title page, declaration, abstracts) is in frontmatter.md.

Placeholders:
  {{TABLE:id|title}}            caption of the table that follows
  {{FIGURE:id|path|title|note}} figure with caption and note
  {{LISTING:id|title}}          caption of the code block that follows
  {{QUERY:key}} / {{RESULT:key}} SPARQL query (Listing) and its result (Table)
  {{SHAPE:name}}                SHACL shape from shacl/shapes.ttl (Listing)
  {{REF:id}}                    "Table 1.1" / "Figure 2.1" / "Listing 4.1"
-->

# Introduction {-}

Over the last three years the number of products based on artificial intelligence (AI) has grown
very quickly. A single company typically offers several *tools* (OpenAI offers ChatGPT and Codex,
Anthropic offers Claude and Claude Code), every tool can use several *models*, and the same model
is often embedded in tools of completely different companies – GitHub Copilot, Cursor and
Perplexity all let the user choose between models from OpenAI, Anthropic and Google. Each tool
also has its own pricing tiers and integrations, and each model is described by its licence,
modalities, context window and benchmark scores. This information is scattered over vendor
pricing pages, model cards and leaderboards, which makes comparing tools laborious.

Such information is naturally a graph: tools, models, providers, licences and benchmarks are
interlinked entities, and the interesting questions follow paths through them (for example
"which free tools run on an openly licensed model that scores well on MMLU?"). Knowledge graphs
represent exactly this kind of interlinked data and allow such questions to be answered with
a single query (Hogan et al., 2021).

**Goal.** The goal of this work is to design and build a knowledge graph of AI tools that can
answer practical selection and market-analysis questions, and to practise the whole process of
designing, populating, querying and validating RDF data.

**Method.** We followed the competency-question-driven approach to ontology engineering
(Grüninger & Fox, 1995; Noy & McGuinness, 2001) in these steps:

- definition of the use case and of ten competency questions (Chapter 1),
- identification of concepts, design of the ontology in OWL 2 and research of reusable
  vocabularies in Linked Open Vocabularies (Chapter 2),
- creation of the knowledge graph data in Turtle (Chapter 3),
- translation of the competency questions and five additional analytical questions into SPARQL
  and interpretation of the results (Chapter 4),
- definition of SHACL shapes and validation of the data, including intentionally invalid data
  (Chapter 5).

All steps are automated by a build script that parses all files, checks the documentation of the
ontology, runs an OWL 2 RL reasoner, executes the queries and the validation, and inserts the
results into this report, so that all numbers in the text correspond to the actual data. All
artefacts are published in a public Git repository (Appendix A).

# Domain description

## Motivation and use case

The knowledge graph serves as a **catalogue and decision-support tool for selecting AI tools**.
Its typical users are:

- **IT and procurement departments** comparing tools by price, integrations and licensing (for
  example "we need a coding assistant for VS Code and JetBrains for less than 25 USD per user"),
- **software developers** choosing a coding assistant or an open-weights model to run locally,
- **analysts and journalists** observing the market – which providers depend on whose models,
  how quickly model generations follow each other and how open-weights models compare with
  closed ones.

The knowledge graph is a manually curated snapshot of the market as of 30 September 2025; the
reasons for this cut-off date are discussed in Section 3.2.

## Competency questions

The knowledge graph must be able to answer the competency questions (CQ) listed in
{{REF:tab:cq}}. Questions CQ3, CQ5, CQ6 and CQ8 have an analytical character (aggregation,
comparison). Five further queries (Q11–Q15) exercise more advanced SPARQL features and are
described in Chapter 4.

{{TABLE:tab:cq|Competency questions}}

| ID | Competency question |
|---|---|
| CQ1 | Which AI tools support code generation and can be used inside Visual Studio Code, and who provides them? |
| CQ2 | Which AI models accept images as input and produce text, who develops them and in how many tools are they used? |
| CQ3 | What is the average, minimum and maximum monthly price of paid plans per provider? |
| CQ4 | Which openly licensed (open-weights) models perform best on MMLU, and how large are they? |
| CQ5 | How many AI tools support each task, and which ones? |
| CQ6 | Which AI tools are powered by models of a different provider than the one offering the tool? |
| CQ7 | What is the complete lineage (all predecessors) of a given model and how far apart were the releases? |
| CQ8 | Which language model has the largest context window for each provider? |
| CQ9 | Which providers offer both text generation and image generation, and with which in-house image models? |
| CQ10 | Which AI tools can be used for free and run on at least one openly licensed model? |

# Ontology design

## Core concepts

From the competency questions we identified the core concepts of the domain. The central design
decision is the separation of an **AI tool** (a product a user interacts with, such as ChatGPT)
from an **AI model** (a trained model, such as GPT-5). Without this distinction questions CQ2,
CQ6, CQ7 or CQ10 could not be expressed. Two concepts were added to the eight initially proposed
ones:

- **BenchmarkResult** – a score is a property of the *pair* (model, benchmark), not of the model
  or the benchmark alone. It is therefore modelled as an n-ary relation, i.e. a separate node
  linking the model, the benchmark and the score, following the W3C pattern for n-ary relations
  (Noy & Rector, 2006) and the class `mls:ModelEvaluation` of the W3C ML Schema (Publio et al., 2018).
- **PricingPlan** – needed for price comparisons (CQ3, CQ10). A plan is a separate entity because
  one plan can cover several tools; for example the *Claude Pro* subscription covers both Claude
  and Claude Code, and *ChatGPT Plus* covers ChatGPT and Codex.

The ontology namespace is `https://otavlna.github.io/4iz444-ai-tools-kg/ontology#` (prefix `ait:`);
instance data use `https://otavlna.github.io/4iz444-ai-tools-kg/data/` (prefix `aid:`). The 13
classes are listed in {{REF:tab:classes}}, the 15 object properties in {{REF:tab:objprops}} and
the 10 datatype properties in {{REF:tab:dataprops}}.

{{TABLE:tab:classes|Classes of the ontology}}

| Class | Superclass | Description |
|---|---|---|
| `ait:AITool` | `schema:SoftwareApplication` | End-user AI product (ChatGPT, Claude Code, Midjourney, …). |
| `ait:AIModel` | `mls:Model` | A specific trained model release (GPT-5, Claude Sonnet 4.5, …). |
| `ait:LanguageModel` | `ait:AIModel` | Model whose primary output is text or code. |
| `ait:ImageGenerationModel` | `ait:AIModel` | Model whose primary output is images. |
| `ait:Provider` | `schema:Organization` | Organisation developing models and/or offering tools. |
| `ait:Task` | – (close match `mls:Task`) | Kind of work: code generation, summarisation, … |
| `ait:Modality` | – | Data type consumed or produced: text, image, audio, video. |
| `ait:License` | `dcterms:LicenseDocument` | Licence under which a model is available. |
| `ait:OpenLicense` | `ait:License` | Licence allowing download and use of the weights. |
| `ait:Integration` | – | Platform or interface of a tool (VS Code, Slack, REST API, …). |
| `ait:Benchmark` | `schema:Dataset` | Standardised evaluation (MMLU, SWE-bench Verified, …). |
| `ait:BenchmarkResult` | `mls:ModelEvaluation` | Score of one model on one benchmark (n-ary relation). |
| `ait:PricingPlan` | `schema:Offer` | Subscription tier with a monthly price. |

{{TABLE:tab:objprops|Object properties of the ontology}}

| Property | Domain → Range | Characteristics | Description |
|---|---|---|---|
| `ait:providedBy` | AITool → Provider | functional; ⊑ `schema:provider` | Organisation that offers the tool. |
| `ait:poweredBy` | AITool → AIModel | | Model used by the tool. |
| `ait:developedBy` | AIModel → Provider | inverse of `develops`; ⊑ `schema:creator` | Organisation that trained the model. |
| `ait:develops` | Provider → AIModel | inverse of `developedBy` | Models released by the provider. |
| `ait:supportsTask` | AITool → Task | | Task the tool can be used for. |
| `ait:inputModality` | AIModel → Modality | | Accepted input modality. |
| `ait:outputModality` | AIModel → Modality | | Produced output modality. |
| `ait:hasLicense` | AIModel → License | ⊑ `dcterms:license` | Licence of the model. |
| `ait:integratesWith` | AITool → Integration | | Platform in which the tool is available. |
| `ait:hasPricingPlan` | AITool → PricingPlan | | Plan under which the tool is offered. |
| `ait:evaluatedModel` | BenchmarkResult → AIModel | functional | Model the result belongs to. |
| `ait:onBenchmark` | BenchmarkResult → Benchmark | functional | Benchmark of the result. |
| `ait:measuresTask` | Benchmark → Task | | Task the benchmark measures. |
| `ait:derivedFrom` | AIModel → AIModel | transitive | Successor or derivative of an earlier model. |
| `ait:competesWith` | AITool → AITool | symmetric, irreflexive | Direct market competitors. |

{{TABLE:tab:dataprops|Datatype properties of the ontology}}

| Property | Domain → Range | Characteristics | Description |
|---|---|---|---|
| `ait:releaseDate` | AITool ⊔ AIModel → `xsd:date` | functional; ⊑ `dcterms:issued` | First public availability. |
| `ait:contextWindow` | LanguageModel → `xsd:integer` | functional | Maximum tokens per request. |
| `ait:parameterCount` | AIModel → `xsd:decimal` | functional | Parameters in billions (if published). |
| `ait:score` | BenchmarkResult → `xsd:decimal` | functional | Score in percent (0–100). |
| `ait:metric` | Benchmark → `xsd:string` | functional | Metric of the benchmark (accuracy, pass@1, …). |
| `ait:monthlyPrice` | PricingPlan → `xsd:decimal` | functional | Price per user per month; 0 means free. |
| `ait:currency` | PricingPlan → `xsd:string` | functional | ISO 4217 currency code. |
| `ait:foundedYear` | Provider → `xsd:gYear` | functional | Year the provider was founded. |
| `ait:headquartersCountry` | Provider → `xsd:string` | | Country of the headquarters. |
| `ait:spdxId` | License → `xsd:string` | functional | SPDX licence identifier. |

Names of all entities are given by `rdfs:label`, homepages by the reused `foaf:homepage`. Every
class and property of the ontology has an `rdfs:label` and an `rdfs:comment`; this is checked
automatically by the build script.

## Axioms and constraints

Besides domain and range restrictions for all 25 properties, the ontology (W3C OWL Working Group,
2012) contains the following axioms:

- **class hierarchy** – `LanguageModel ⊑ AIModel`, `ImageGenerationModel ⊑ AIModel`,
  `OpenLicense ⊑ License`, and alignment of the main classes to external superclasses
  (schema.org, ML Schema, Dublin Core),
- **disjointness** – `owl:AllDisjointClasses` over the ten top-level classes (a tool cannot be a
  model, a provider cannot be a task, …) and `LanguageModel owl:disjointWith ImageGenerationModel`,
- **property characteristics** – functional properties (`providedBy`, `evaluatedModel`,
  `onBenchmark`, `releaseDate`, `score`, `monthlyPrice` and others), an inverse pair
  (`developedBy` / `develops`), a transitive property (`derivedFrom`, the lineage of a model)
  and a symmetric and irreflexive property (`competesWith`),
- **union domain** – `releaseDate` is applicable to both tools and models
  (`rdfs:domain [ owl:unionOf (ait:AITool ait:AIModel) ]`),
- **sub-properties** of reused vocabularies (`hasLicense ⊑ dcterms:license`,
  `releaseDate ⊑ dcterms:issued`, `providedBy ⊑ schema:provider`, `developedBy ⊑ schema:creator`).

The property `derivedFrom` is only transitive, not irreflexive: OWL 2 DL does not allow
irreflexivity on transitive (non-simple) properties. The rule "a model cannot be derived from a
newer model" is therefore enforced by SHACL (shape S10 in Chapter 5).

The ontology is valid Turtle (Beckett et al., 2014); all reused external terms are explicitly
declared so that it can be loaded into Protégé as OWL 2. It is free of logical inconsistencies:
{{CONSISTENCY}}

## Conceptual model

The conceptual model of the ontology is shown in {{REF:fig:model}}. The diagram is generated
automatically from the Turtle file, so it always corresponds to the actual ontology. The two
central classes are `AITool` and `AIModel`, connected by `poweredBy`; `BenchmarkResult` and
`PricingPlan` are the auxiliary nodes that carry numeric values for the analytical queries.

{{FIGURE:fig:model|figures/ontology.png|Conceptual model of the AI Tools Catalogue ontology|Note: Own work. Blue boxes are top-level classes, yellow boxes are subclasses (dashed arrows = rdfs:subClassOf). Solid arrows are object properties from domain to range; datatype properties are listed inside the classes. F = functional, T = transitive, S = symmetric, I = irreflexive.}}

## Reuse of existing ontologies

We searched Linked Open Vocabularies (Vandenbussche et al., 2017), schema.org (Guha et al., 2016)
and W3C specifications for terms that cover our concepts. The most relevant candidates are
summarised in {{REF:tab:reuse}}.

{{TABLE:tab:reuse|Candidate vocabularies for reuse}}

| Vocabulary | Relevant terms | Fit for our domain |
|---|---|---|
| schema.org | `SoftwareApplication`, `Organization`, `Offer`, `price`, `priceCurrency`, `provider`, `creator`, `Dataset`, `isBasedOn`, `sameAs` | Very good for products, organisations and offers; no notion of AI models, modalities or benchmarks. |
| W3C ML Schema (`mls:`) | `Model`, `ModelEvaluation`, `EvaluationMeasure`, `Task`, `Implementation` | Designed for machine-learning experiments; models and evaluations map well. Its `Task` means an ML task (classification, regression), which is only close to our user-facing task. |
| Dublin Core Terms | `license`, `LicenseDocument`, `issued`, `created`, `creator`, `title` | Standard metadata (DCMI Usage Board, 2020); ideal for licences and dates. |
| FOAF | `Organization`, `homepage` | Widely used (Brickley & Miller, 2014); `homepage` directly reusable. |
| SKOS | `Concept`, `ConceptScheme`, `broader`, `exactMatch`, `closeMatch` | Suitable for controlled lists (tasks, modalities) and alignments (Miles & Bechhofer, 2009). |
| SPDX License List | licence identifiers | Standard identifiers of licences such as Apache-2.0 or MIT (SPDX Workgroup, n.d.). |
| Wikidata | entities of providers (OpenAI Q21708200, Google Q95, Meta Q380, GitHub Q364) | Links of instances to the Linked Open Data cloud. |

**Decision.** We define our **own core classes and properties** in the `ait:` namespace and
**align** them with the external vocabularies instead of using the external terms directly,
for three reasons:

- *Precise semantics and constraints.* We need domain and range restrictions, disjointness and
  functional properties (for example "a tool has exactly one provider"). Asserting such axioms on
  `schema:provider` or `mls:Model` would change the meaning of terms we do not own and would
  conflict with their intentionally loose definitions (schema.org uses `domainIncludes` and
  `rangeIncludes` instead of strict domains and ranges).
- *Missing concepts.* No vocabulary covers the distinction between a tool and a model,
  modalities, context windows or pricing plans shared by several products.
- *Interoperability is preserved* through `rdfs:subClassOf` (for example
  `ait:AITool ⊑ schema:SoftwareApplication`, `ait:BenchmarkResult ⊑ mls:ModelEvaluation`),
  `rdfs:subPropertyOf` (`ait:hasLicense ⊑ dcterms:license`, `ait:releaseDate ⊑ dcterms:issued`)
  and `skos:closeMatch` (`ait:Task` and `mls:Task`). An application that understands schema.org
  or Dublin Core can therefore still interpret our data after RDFS reasoning.

Some terms are **reused directly** because their semantics fits exactly and no additional
constraints are needed: `rdfs:label` (names), `foaf:homepage` (homepages), `schema:sameAs` (links
of providers to Wikidata), `schema:isBasedOn` (output of the CONSTRUCT query Q15), Dublin Core and
VANN for the ontology metadata, and SPDX identifiers as values of `ait:spdxId`.

# Knowledge graph data

## Data creation

The knowledge graph (file `data/ai-tools-data.ttl`) was created manually with the help of a large
language model, based on publicly available information (vendor pricing pages, model cards and
release announcements), and then reviewed by the authors. It covers 15 tools from 12 providers
and 27 models. Besides the tools named in the original topic (ChatGPT, Claude, Gemini, Midjourney,
GitHub Copilot) it includes coding agents (Claude Code, OpenAI Codex, Cursor, Gemini Code Assist),
an AI search engine (Perplexity), chat applications of open-weights providers (Meta AI, Le Chat,
DeepSeek Chat, Qwen Chat) and a tool for running models locally (Ollama). Prices are list prices
with monthly billing. Benchmark scores are mostly reported by the vendors themselves and were
measured under different settings (number of shots, use of tools, reasoning mode), so they are
indicative and serve to demonstrate analytical queries, not as an authoritative leaderboard.

## Time scope of the snapshot

The data describe the state of the market as of **30 September 2025**; the newest model in the
graph is Claude Sonnet 4.5, released on 29 September 2025. Models and price changes released
after this date (late 2025 and 2026) are deliberately not included, for the following reasons:

- *Internal consistency.* Prices, model line-ups and benchmark results change every few weeks.
  A graph that mixes facts valid at different dates would produce misleading comparisons (for
  example a 2026 model compared with 2025 prices of its competitors). All facts in the graph
  therefore refer to a single cut-off date.
- *Verifiability.* The data were generated with the help of a language model whose reliable
  knowledge ends around this period, and were reviewed against public sources. Extending the
  graph to later releases without the same verification would risk invented values, which is
  worse than an explicitly dated snapshot.
- *Comparable benchmarks.* For newer models vendors increasingly report results on newer
  benchmarks, so their scores on the five benchmarks used here are often not available.
- *Purpose of the work.* The goal is to practise modelling, querying and validation; the
  structure of the graph does not depend on the snapshot.

Updating the graph is straightforward: a new model is described by about ten triples
(see the example in {{REF:lst:example}}), the SHACL shapes check that the new data are complete
and well-formed, and query Q14 lists models that are used by tools but still lack benchmark
results.

## Statistics

The size of the ontology and of the knowledge graph is summarised in {{REF:tab:stats}} and the
number of instances per class in {{REF:tab:instances}}. All classes and all properties except
`ait:develops` are used in the data; `ait:develops` is the inverse of `ait:developedBy` and its
values are inferred by the reasoner.

{{TABLE:tab:stats|Size of the ontology and of the knowledge graph}}

{{STATS_SUMMARY}}

{{TABLE:tab:instances|Number of instances per class (including instances of subclasses)}}

{{STATS_CLASSES}}

{{REF:lst:example}} shows an example of the data – a tool, a model and a benchmark result.

{{LISTING:lst:example|Example triples of the knowledge graph (Turtle)}}

```turtle
aid:GitHubCopilot a ait:AITool ;
    rdfs:label "GitHub Copilot" ;
    ait:providedBy aid:GitHub ;
    ait:releaseDate "2022-06-21"^^xsd:date ;
    ait:poweredBy aid:GPT41 , aid:GPT5 , aid:ClaudeSonnet45 , aid:Gemini25Pro ;
    ait:supportsTask aid:CodeGeneration , aid:CodeCompletion , aid:CodeReview ;
    ait:integratesWith aid:VSCode , aid:JetBrains , aid:GitHubPlatform , aid:CLI ;
    ait:hasPricingPlan aid:CopilotFree , aid:CopilotPro , aid:CopilotProPlus , aid:CopilotBusiness ;
    ait:competesWith aid:Cursor .

aid:ClaudeSonnet45 a ait:LanguageModel ;
    rdfs:label "Claude Sonnet 4.5" ;
    ait:developedBy aid:Anthropic ;
    ait:releaseDate "2025-09-29"^^xsd:date ;
    ait:contextWindow 200000 ;
    ait:inputModality aid:Text , aid:Image ;
    ait:outputModality aid:Text ;
    ait:hasLicense aid:Proprietary ;
    ait:derivedFrom aid:ClaudeSonnet4 .

aid:R_SWE_ClaudeSonnet45 a ait:BenchmarkResult ;
    ait:evaluatedModel aid:ClaudeSonnet45 ;
    ait:onBenchmark aid:SWEbenchVerified ;
    ait:score 77.2 .
```

A second file, `data/ai-tools-data-invalid.ttl`, contains eleven intentionally broken resources
used to test the SHACL shapes (Section 5.11).

# SPARQL queries

All queries (Harris & Seaborne, 2013) are stored in the directory `queries/` and were executed
with RDFLib over the union of the ontology and the data; the ontology is needed for
`rdfs:subClassOf*` paths. The results are inserted into this chapter automatically by the build
script. The prefixes in {{REF:lst:prefixes}} are declared in every query file and are omitted from
the listings for brevity.

{{LISTING:lst:prefixes|Prefixes used in all queries}}

```sparql
PREFIX ait:  <https://otavlna.github.io/4iz444-ai-tools-kg/ontology#>
PREFIX aid:  <https://otavlna.github.io/4iz444-ai-tools-kg/data/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
```

## CQ1: Coding tools available in Visual Studio Code

The query ({{REF:lst:cq01}}) is a simple conjunctive query combining a task, an integration and a
property path (`ait:providedBy/rdfs:label`) to the name of the provider.

{{QUERY:cq01}}

{{RESULT:cq01}}

Four tools satisfy both conditions ({{REF:tab:cq01}}). Cursor is not listed because it is a
stand-alone editor (a desktop application) rather than a VS Code extension; chat assistants such
as ChatGPT generate code but do not integrate into the IDE.

## CQ2: Models with image input and text output

The class is matched with `a/rdfs:subClassOf* ait:AIModel`, so the query ({{REF:lst:cq02}}) works
for instances of any subclass. `OPTIONAL` together with `COUNT(DISTINCT)` adds the number of tools
using the model; it is 0 for models that are in the graph only as predecessors of newer models.

{{QUERY:cq02}}

{{RESULT:cq02}}

Multimodal input has become the norm: 16 of the 22 language models accept images
({{REF:tab:cq02}}). The most widely used ones are the flagships of the three large labs
(Claude Sonnet 4.5, GPT-5, Gemini 2.5 Pro), each used in five tools – their own and those of third
parties.

## CQ3: Average price of paid plans per provider

Because one plan can be linked to several tools of the same provider, the inner sub-query
({{REF:lst:cq03}}) first selects `DISTINCT` (provider, plan) pairs; the outer query aggregates them
with `COUNT`, `AVG`, `MIN` and `MAX` and rounds the average to two decimal places.

{{QUERY:cq03}}

{{RESULT:cq03}}

The averages in {{REF:tab:cq03}} are dominated by premium tiers: Perplexity, Google, Anysphere
(Cursor) and OpenAI each have a tier for 200–250 USD, whereas the entry-level paid tier costs
almost universally 20 USD. GitHub has the lowest average price of paid plans (22.67 USD) and
shares the cheapest entry tier (10 USD) with Midjourney. Le Chat is priced in EUR, which is why the
currency is part of the grouping – averaging prices in different currencies would be meaningless.

## CQ4: Best open-weights models on MMLU

The licence is matched by its class (`a ait:OpenLicense`) and the score is obtained through the
n-ary `BenchmarkResult` node ({{REF:lst:cq04}}).

{{QUERY:cq04}}

{{RESULT:cq04}}

Openly licensed models reach the level of closed models on MMLU ({{REF:tab:cq04}}; for comparison,
GPT-4.1 scores 90.2 and GPT-4o 88.7). Model size helps but is not decisive: the 117-billion-
parameter gpt-oss-120b scores almost as well as the 671-billion-parameter DeepSeek-R1, and the
small Mistral Small 3.1 (24B) and Gemma 3 (27B) are only about 10 points behind models more than
fifteen times larger.

## CQ5: Number of tools per task

The query ({{REF:lst:cq05}}) groups the tools by task with `COUNT` and `GROUP_CONCAT`; the
sub-query with `ORDER BY` makes the concatenated lists alphabetical and the results reproducible.

{{QUERY:cq05}}

{{RESULT:cq05}}

Code generation is the most common capability – 12 of the 15 tools support it ({{REF:tab:cq05}}),
because practically every general-purpose assistant can write code. Only specialised coding tools
offer code review and inline code completion. The task *Knowledge and reasoning* does not appear,
because it is used only to classify benchmarks, not tools.

## CQ6: Tools built on models of other providers

The key condition of the query ({{REF:lst:cq06}}) is `FILTER (?tp != ?mp)`: the provider of the
tool differs from the developer of the model.

{{QUERY:cq06}}

{{RESULT:cq06}}

Four tools have no in-house models at all ({{REF:tab:cq06}}). GitHub Copilot, Cursor and
Perplexity all depend on the same three labs (OpenAI, Anthropic, Google), which illustrates how
concentrated the model layer of the market is. Ollama, a tool for running models locally, depends
on six providers, all of which publish open weights.

## CQ7: Model lineage

The transitive relation `ait:derivedFrom` is followed with the property path `ait:derivedFrom+`
({{REF:lst:cq07}}). The difference of two `xsd:date` values is an `xsd:duration` (for example
`P130D`), from which the number of days is extracted with `REPLACE` and cast to an integer.

{{QUERY:cq07}}

{{RESULT:cq07}}

The data assert only the direct predecessors (Sonnet 4.5 → Sonnet 4 → 3.7 Sonnet → 3.5 Sonnet),
but the property path returns the whole chain ({{REF:tab:cq07}}). In both lineages the latest
model followed its direct predecessor after 113–130 days; the earlier steps were longer (for
example 249 days between Claude 3.5 Sonnet and 3.7 Sonnet). Two short lineages are not enough to
generalise about release cycles – the query only shows how such an analysis can be done once the
graph contains more model generations.

## CQ8: Largest context window per provider

A sub-query computes the maximum context window per provider ({{REF:lst:cq08}}); it is joined back
to the models to find which model or models reach it, and ties are aggregated with `GROUP_CONCAT`.

{{QUERY:cq08}}

{{RESULT:cq08}}

Google, OpenAI (GPT-4.1) and Meta (Llama 4 Maverick) offer context windows of about one million
tokens ({{REF:tab:cq08}}). All Anthropic models in the graph share the same 200,000-token window,
so five models tie for the maximum.

## CQ9: Providers offering both text and image generation

Two independent patterns for tools of the same provider (`?t1`, `?t2`) express that the provider
offers both tasks; an `OPTIONAL` block looks for an image model developed by the same provider
({{REF:lst:cq09}}).

{{QUERY:cq09}}

{{RESULT:cq09}}

OpenAI and Google cover both tasks with their own image models, gpt-image-1 and Imagen 4
({{REF:tab:cq09}}). Meta AI also generates images, but no Meta image model is part of the graph –
the query reveals a gap in the data that could be filled in a future version. Midjourney is not
listed because it only generates images.

## CQ10: Free tools running on openly licensed models

The query ({{REF:lst:cq10}}) joins tools, pricing plans with a price of 0 and models whose licence
is an instance of `ait:OpenLicense`.

{{QUERY:cq10}}

{{RESULT:cq10}}

Five tools can be used free of charge with an open-weights model ({{REF:tab:cq10}}). Ollama stands
out with six such models because it runs them locally on the user's hardware; DeepSeek Chat,
Meta AI and Qwen Chat are hosted chat applications of providers that publish the weights of their
models.

## Q11: Best scores of providers compared with the benchmark average

This analytical query ({{REF:lst:q11}}) has two levels of aggregation: the sub-query computes the
average score per benchmark (only benchmarks with at least five results are considered) and the
outer query takes the best model of each provider (`MAX`) and computes its difference from the
average in percentage points.

{{QUERY:q11}}

{{RESULT:q11}}

The spread is largest on the agentic coding benchmark SWE-bench Verified ({{REF:tab:q11}}), where
the best Anthropic model is 12.7 points above the average and DeepSeek 15.3 points below it. On the
older MMLU benchmark the results are saturated – the best models of five providers are within
4 points of the average, and only the smaller models (Mistral Small 3.1, Gemma 3 27B) fall clearly
behind.

## Q12: Analysis of model names with string functions

The query ({{REF:lst:q12}}) uses `REGEX`, `REPLACE` with a capturing group, `STRBEFORE`, `STRAFTER`
and `UCASE` to split names at their first version number into a model family and a version label
(for example "Claude Sonnet 4.5" into "CLAUDE SONNET" and "4.5"), and then aggregates the releases
per family with `HAVING (COUNT(?m) > 1)`.

{{QUERY:q12}}

{{RESULT:q12}}

The query recovers model families purely from naming conventions ({{REF:tab:q12}}), which also
shows the limits of this approach:

- The version label is everything after the family name, so it keeps letter suffixes and variant
  names: GPT-4o appears as "4o", not as "4", and the Gemini family contains two models with the
  version number 2.5 that differ only in the variant ("2.5 Pro" and "2.5 Flash"). The same version
  number therefore does not imply the same model.
- Anthropic changed its naming scheme from "Claude 3.7 Sonnet" to "Claude Sonnet 4", so one product
  line is split into the two families CLAUDE and CLAUDE SONNET.

The explicit relation `ait:derivedFrom` (CQ7) is therefore the reliable way to express lineage;
string analysis is useful only as a quick, approximate overview.

## Q13: Competitor network

The relation `competesWith` is declared symmetric but is stated in only one direction in the
data; the alternative path `ait:competesWith|^ait:competesWith` follows both directions without
reasoning ({{REF:lst:q13}}). `EXISTS` inside `IF` tests whether two competitors share an
underlying model.

{{QUERY:q13}}

{{RESULT:q13}}

ChatGPT has the most direct competitors ({{REF:tab:q13}}). In the coding segment (GitHub Copilot,
Cursor, Claude Code, OpenAI Codex) competitors almost always share models – they compete on the
product rather than on the model. In the chat segment competitors mostly use their own models;
Claude, Le Chat and DeepSeek Chat share no model with any of their competitors.

## Q14: Models used in tools but lacking benchmark results

`FILTER NOT EXISTS` finds language models that are used by at least one tool but have no
`BenchmarkResult` ({{REF:lst:q14}}). This is a data-quality check that identifies gaps in the
graph.

{{QUERY:q14}}

{{RESULT:q14}}

Two models used in production tools lack benchmark data in the graph ({{REF:tab:q14}}) and are
candidates for the next data update.

## Q15: Materialising tool dependencies with CONSTRUCT

The `CONSTRUCT` query ({{REF:lst:q15}}) derives new knowledge: a direct link `schema:isBasedOn`
from a tool to every external provider whose model it uses. The resulting graph
({{REF:lst:q15res}}, stored in `results/q15-construct-tool-dependency.ttl`) could be added to the
knowledge graph to answer dependency questions without the two-step path.

{{QUERY:q15}}

{{RESULT:q15}}

# SHACL validation

The shapes (Knublauch & Kontokostas, 2017) are stored in `shacl/shapes.ttl` and were validated
with pySHACL. They are organised into ten groups S1–S10 consisting of eleven node shapes; together
they target every class of the ontology (`ait:OpenLicense` is covered through its superclass
`ait:License`). Shape S10 uses a SPARQL-based constraint.

## S1 AIToolShape

Every tool has a name of type `xsd:string`, exactly one provider (`sh:minCount 1` and
`sh:maxCount 1`, value of class `ait:Provider`), at least one model of class `ait:AIModel`, at
least one task and at least one pricing plan ({{REF:lst:AIToolShape}}).

{{SHAPE:AIToolShape}}

## S2 AIModelShape

Every model has exactly one developer, exactly one release date of type `xsd:date`, exactly one
licence and at least one input and one output modality. The context window and the parameter
count are optional, but when present they must be single positive numbers of the right datatype,
expressed with `sh:minExclusive 0` ({{REF:lst:AIModelShape}}).

{{SHAPE:AIModelShape}}

## S3 LanguageModelShape and ImageGenerationModelShape

These shapes add subclass-specific rules: a language model must state its context window and must
output text (`sh:hasValue aid:Text`), and an image generation model must output images
({{REF:lst:LanguageModelShape}} and {{REF:lst:ImageGenerationModelShape}}).

{{SHAPE:LanguageModelShape}}

{{SHAPE:ImageGenerationModelShape}}

## S4 BenchmarkResultShape

Every result refers to exactly one model and one benchmark and has exactly one decimal score in
the interval [0, 100], expressed with `sh:minInclusive` and `sh:maxInclusive`
({{REF:lst:BenchmarkResultShape}}).

{{SHAPE:BenchmarkResultShape}}

## S5 PricingPlanShape

Every plan has a name and exactly one non-negative decimal price, and the currency must be one of
the supported codes, expressed with `sh:in ("USD" "EUR")` ({{REF:lst:PricingPlanShape}}).

{{SHAPE:PricingPlanShape}}

## S6 ProviderShape

Every provider has a name and a headquarters country; the founding year, if stated, must be a
single value of type `xsd:gYear`, and the homepage must be an IRI rather than a string literal
(`sh:nodeKind sh:IRI`) ({{REF:lst:ProviderShape}}).

{{SHAPE:ProviderShape}}

## S7 LicenseShape

Every licence has exactly one SPDX identifier. The regular expression in `sh:pattern` accepts
identifiers from the SPDX License List (for example `Apache-2.0`) as well as custom identifiers
with the prefix `LicenseRef-`, which SPDX prescribes for licences that are not on the list
({{REF:lst:LicenseShape}}).

{{SHAPE:LicenseShape}}

## S8 BenchmarkShape

Every benchmark measures at least one task and states exactly one metric in which its scores are
expressed ({{REF:lst:BenchmarkShape}}).

{{SHAPE:BenchmarkShape}}

## S9 VocabularyShape

Tasks, modalities and integrations are controlled vocabularies whose instances are shown to users
by name. One shape with three target classes requires that each of them has exactly one name
({{REF:lst:VocabularyShape}}).

{{SHAPE:VocabularyShape}}

## S10 ModelLineageShape

A model cannot have been released before a model it is derived from. This temporal rule compares
values of two different nodes and cannot be expressed with core SHACL constraints, so a
`sh:SPARQLConstraint` is used; every row returned by the `SELECT` query is reported as a violation
({{REF:lst:ModelLineageShape}}).

{{SHAPE:ModelLineageShape}}

## Validation results

The valid knowledge graph (`data/ai-tools-data.ttl`) conforms to all shapes:
{{SHACL_VALID}}

To test the shapes, the knowledge graph was validated together with the file
`data/ai-tools-data-invalid.ttl`. The file contains eleven broken resources: a tool without a
provider and a pricing plan, a tool "powered by" a provider instead of a model, a model with a
string release date, a negative context window, no licence and audio-only output, an image model
producing only text, a benchmark result with a score of 112.5 and no benchmark, a plan with a
negative price in CZK, a model released before its predecessor, a provider with an integer
founding year, no country and a string homepage, a licence with an invalid SPDX identifier, a
benchmark without a task and a metric, and a task with two names. The violations found are listed
in {{REF:tab:shacl}}.

{{TABLE:tab:shacl|SHACL violations found in the intentionally invalid data}}

{{SHACL_INVALID}}

Every intentionally introduced error was detected by the expected shape and constraint component,
and the valid data conform to all shapes. This shows that the shapes are neither too weak nor too
strict for the real data.

# Conclusion {-}

The goal of the work – to design and build a knowledge graph of AI tools that answers practical
selection and market-analysis questions – was achieved. We designed an ontology with 13 classes,
25 properties and a range of OWL axioms, populated it with a knowledge graph of almost 1,000
triples, answered ten competency questions and five additional analytical queries in SPARQL, and
validated the data with eleven SHACL shapes that cover every class of the ontology.

The most valuable modelling decisions were the separation of tools from models and the modelling
of benchmark results and pricing plans as separate nodes. They enable the most interesting
analyses: dependencies between providers (CQ6, Q15), price comparisons (CQ3) and comparison of
models with benchmark averages (Q11). The queries also showed, for example, that third-party
tools such as GitHub Copilot, Cursor and Perplexity rely on the models of the same three providers,
and that openly licensed models reach the level of closed models on older benchmarks.

**Limitations.** The data are a manually created snapshot as of 30 September 2025 and will age
quickly; benchmark scores are mostly vendor-reported under different settings, and some
conclusions (for example about release intervals in CQ7) are based on only a few data points.

**Future work.** A natural next step would be to populate the graph automatically from
structured sources (for example Hugging Face model cards, Wikidata and public leaderboards) using
YARRRML or RML mappings, to track prices and benchmark results over time, to add API pricing per
token and to extend the `Task` concept into a SKOS hierarchy (for example *code completion* as a
narrower concept of *code generation*).

# References {-}

Beckett, D., Berners-Lee, T., Prud'hommeaux, E., & Carothers, G. (2014). *RDF 1.1 Turtle: Terse RDF triple language* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/turtle/

Brickley, D., & Miller, L. (2014). *FOAF vocabulary specification 0.99*. http://xmlns.com/foaf/spec/

DCMI Usage Board. (2020). *DCMI metadata terms*. Dublin Core Metadata Initiative. https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

Grüninger, M., & Fox, M. S. (1995). Methodology for the design and evaluation of ontologies. In *Proceedings of the Workshop on Basic Ontological Issues in Knowledge Sharing, IJCAI-95*. Montreal, Canada.

Guha, R. V., Brickley, D., & Macbeth, S. (2016). Schema.org: Evolution of structured data on the web. *Communications of the ACM, 59*(2), 44–51. https://doi.org/10.1145/2844544

Harris, S., & Seaborne, A. (Eds.). (2013). *SPARQL 1.1 query language* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/sparql11-query/

Hogan, A., Blomqvist, E., Cochez, M., d'Amato, C., de Melo, G., Gutierrez, C., Kirrane, S., Labra Gayo, J. E., Navigli, R., Neumaier, S., Ngonga Ngomo, A.-C., Polleres, A., Rashid, S. M., Rula, A., Schmelzeisen, L., Sequeda, J., Staab, S., & Zimmermann, A. (2021). Knowledge graphs. *ACM Computing Surveys, 54*(4), Article 71. https://doi.org/10.1145/3447772

Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes Constraint Language (SHACL)* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/shacl/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS Simple Knowledge Organization System reference* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

Noy, N., & Rector, A. (Eds.). (2006). *Defining n-ary relations on the Semantic Web* (W3C Working Group Note). World Wide Web Consortium. https://www.w3.org/TR/swbp-n-aryRelations/

Noy, N. F., & McGuinness, D. L. (2001). *Ontology development 101: A guide to creating your first ontology* (Technical Report KSL-01-05). Stanford Knowledge Systems Laboratory.

Publio, G. C., Esteves, D., Ławrynowicz, A., Panov, P., Soldatova, L., Soru, T., Vanschoren, J., & Zafar, H. (2018). *ML-Schema: Exposing the semantics of machine learning with schemas and ontologies*. arXiv. https://doi.org/10.48550/arXiv.1807.05351

SPDX Workgroup. (n.d.). *SPDX license list*. The Linux Foundation. Retrieved November 10, 2026, from https://spdx.org/licenses/

Vandenbussche, P.-Y., Atemezing, G. A., Poveda-Villalón, M., & Vatant, B. (2017). Linked Open Vocabularies (LOV): A gateway to reusable semantic vocabularies on the Web. *Semantic Web, 8*(3), 437–452. https://doi.org/10.3233/SW-160213

W3C OWL Working Group. (2012). *OWL 2 Web Ontology Language document overview (second edition)* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/owl2-overview/

# Appendices {-}

## Repository and reproducibility

All artefacts of the work are available in the public repository
<https://github.com/otavlna/4iz444-ai-tools-kg>. Its structure is described in
{{REF:tab:repo}}.

{{TABLE:tab:repo|Structure of the repository}}

| Path | Content |
|---|---|
| `ontology/ai-tools.ttl` | ontology (OWL 2, Turtle) |
| `data/ai-tools-data.ttl` | knowledge graph |
| `data/ai-tools-data-invalid.ttl` | intentionally invalid data for testing the SHACL shapes |
| `queries/*.rq` | SPARQL queries CQ1–CQ10 and Q11–Q15 |
| `shacl/shapes.ttl` | SHACL shapes S1–S10 |
| `results/` | query results (CSV, Markdown, Turtle) and SHACL reports |
| `scripts/build.py` | build pipeline: parsing, documentation check, reasoning, queries, SHACL, diagram |
| `scripts/build_docx.py` | conversion of the report into the FIS Word template |
| `report/` | source of the report, the template and the resulting DOCX and PDF |

Running `make all` re-creates all results, the diagram and this report from the source files.

## Use of artificial intelligence tools

{{REF:tab:ai}} documents the use of AI tools in individual parts of the work, as required by the
declaration at the beginning of the document.

{{TABLE:tab:ai|Use of AI tools in individual parts of the work}}

| Part of the work | Tool | How the tool was used | Our own contribution |
|---|---|---|---|
| Choice of domain and core classes | – | – | Domain and initial list of classes proposed by Matěj Fadrhons. |
| Ontology | Claude Code (Anthropic) | Drafting classes, properties, axioms and documentation from our list of classes. | Review of the design decisions. |
| Data | Claude Code (Anthropic) | Generating the instance data from public information about tools, models, prices and benchmarks. | Review of the data, decision on the snapshot date. |
| SPARQL queries and SHACL shapes | Claude Code (Anthropic) | Drafting the queries for the competency questions and the shapes. | Review of the competency questions and of the query results. |
| Build scripts | Claude Code (Anthropic) | Generating the source code of the build pipeline. | Running and checking the pipeline. |
| Text of the report | Claude Code (Anthropic) | Drafting and language editing of the text. | Review and corrections of the text. |
| Review of the work | Codex (OpenAI) | Automated review of the report and the data, which identified inaccuracies. | Evaluation of the findings and their correction. |

## Contribution of team members

The contribution of the individual team members is summarised in {{REF:tab:team}}.

{{TABLE:tab:team|Contribution of team members}}

| Team member | Contribution |
|---|---|
| Ota Vlna | Coordination of the work; generation and review of the ontology, data, queries and shapes; repository and build pipeline; text of the report. |
| Matěj Fadrhons | Choice of the domain and of the core classes; review of the report and the data. |
