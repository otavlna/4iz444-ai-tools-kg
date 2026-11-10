---
title: "AI Tools Catalogue — a Knowledge Graph of AI Tools, Models and Providers"
subtitle: "Semestral project, 4IZ444 Knowledge Graphs and Linked Data"
author:
  - Ota Vlna
  - Matěj Fadrhons
date: "Prague University of Economics and Business, winter semester 2026/2027"
lang: en
---

# 1 Domain description

## 1.1 Motivation

Over the last three years the number of AI products has exploded. A single company typically
offers several *tools* (e.g. OpenAI offers ChatGPT and Codex; Anthropic offers Claude and Claude
Code), every tool can use several *models*, and the same model is often embedded in tools of
completely different companies (GitHub Copilot, Cursor and Perplexity all let the user choose
between models from OpenAI, Anthropic and Google). On top of that, each tool has its own pricing
tiers, integrations (IDE plug-ins, Slack, mobile apps, REST API) and each model is described by
licences, modalities, context-window sizes and benchmark scores that are scattered over vendor
blogs, model cards and leaderboards.

This information is naturally a **graph**: tools, models, providers, licences and benchmarks are
interlinked entities, and the interesting questions are about paths through them ("which free
tools run on an open-weights model that scores well on MMLU?"). A spreadsheet or a relational table
per entity type quickly becomes awkward for such questions, whereas a knowledge graph handles them
with a single SPARQL query.

## 1.2 Use case and users

The knowledge graph serves as a **catalogue and decision-support tool for selecting AI tools**.
Typical users are:

* **IT / procurement departments** comparing tools by price, integrations and licensing (e.g. "we
  need a coding assistant for VS Code and JetBrains under 25 USD per user"),
* **software developers** choosing a coding assistant or a model to run locally,
* **analysts and journalists** observing the market — which providers depend on whose models,
  how quickly model generations follow each other, how open-weights models compare to closed ones.

The graph is a snapshot of the market around autumn 2025. It was created manually from public
sources (vendor pricing pages, model cards, announcements); benchmark scores are mostly
vendor-reported and were measured under different settings, so they are indicative and serve to
demonstrate analytical queries rather than as an authoritative leaderboard.

## 1.3 Competency questions

The knowledge graph must be able to answer the following competency questions (CQ). Questions
CQ3, CQ5, CQ6, CQ8 and CQ11 have an analytical character (aggregation, comparison).

| ID | Competency question |
|---|---|
| CQ1 | Which AI tools support code generation and can be used inside Visual Studio Code, and who provides them? |
| CQ2 | Which AI models accept images as input and produce text, who develops them and in how many tools are they used? |
| CQ3 | What is the average, minimum and maximum monthly price of paid plans per provider? |
| CQ4 | Which openly licensed (open-weights) models perform best on MMLU, and how large are they? |
| CQ5 | How many AI tools support each task, and which ones? |
| CQ6 | Which AI tools are powered by models of a *different* provider than the one offering the tool? |
| CQ7 | What is the complete lineage (all predecessors) of a given model and how far apart were the releases? |
| CQ8 | Which language model has the largest context window for each provider? |
| CQ9 | Which providers offer both text generation and image generation, and with which in-house image models? |
| CQ10 | Which AI tools can be used for free and run on at least one openly licensed model? |

In addition, five further queries (Q11–Q15) exercise more advanced SPARQL features (nested
aggregation, string functions, symmetric property paths with `EXISTS`, negation with
`FILTER NOT EXISTS`, and `CONSTRUCT`); see Section 4.

# 2 Ontology design

## 2.1 Core concepts

From the competency questions we identified the following core concepts. The central design
decision is the separation of an **AI tool** (a product a user interacts with — ChatGPT) from an
**AI model** (a trained model — GPT-5). Without this distinction questions CQ2, CQ6, CQ7 or CQ10
cannot be expressed. Two further concepts were added on top of the initially proposed eight:

* **BenchmarkResult** — a score is a property of the *pair* (model, benchmark), not of the model
  or the benchmark alone. We therefore model it as an n-ary relation (a reified "evaluation"
  node), following the W3C pattern *Defining N-ary Relations on the Semantic Web* and the
  `mls:ModelEvaluation` class of the W3C ML Schema.
* **PricingPlan** — needed for price comparisons (CQ3, CQ10). A plan is a separate entity because
  one plan can cover several tools (e.g. the *Claude Pro* subscription covers both Claude and
  Claude Code, *ChatGPT Plus* covers ChatGPT and Codex).

The namespace of the ontology is `https://otavlna.github.io/4iz444-ai-tools-kg/ontology#`
(prefix `ait:`), instance data use `https://otavlna.github.io/4iz444-ai-tools-kg/data/`
(prefix `aid:`).

### Classes (13)

| Class | Superclass | Description |
|---|---|---|
| `ait:AITool` | `schema:SoftwareApplication` | End-user AI product (ChatGPT, Claude Code, Midjourney, …). |
| `ait:AIModel` | `mls:Model` | A specific trained model release (GPT-5, Claude Sonnet 4.5, …). |
| `ait:LanguageModel` | `ait:AIModel` | Model whose primary output is text/code. |
| `ait:ImageGenerationModel` | `ait:AIModel` | Model whose primary output is images. |
| `ait:Provider` | `schema:Organization` | Organisation developing models and/or offering tools. |
| `ait:Task` | — (close match `mls:Task`) | Kind of work: code generation, summarisation, … |
| `ait:Modality` | — | Data type consumed/produced: text, image, audio, video. |
| `ait:License` | `dcterms:LicenseDocument` | Licence under which a model is available. |
| `ait:OpenLicense` | `ait:License` | Licence allowing download and use of the weights (open-weights). |
| `ait:Integration` | — | Platform or interface the tool is available in (VS Code, Slack, REST API, …). |
| `ait:Benchmark` | `schema:Dataset` | Standardised evaluation (MMLU, SWE-bench Verified, …). |
| `ait:BenchmarkResult` | `mls:ModelEvaluation` | Score of one model on one benchmark (n-ary relation). |
| `ait:PricingPlan` | `schema:Offer` | Subscription tier with a monthly price. |

### Object properties (15)

| Property | Domain → Range | Characteristics | Description |
|---|---|---|---|
| `ait:providedBy` | AITool → Provider | functional; ⊑ `schema:provider` | Organisation that offers the tool. |
| `ait:poweredBy` | AITool → AIModel | | Model used by the tool. |
| `ait:developedBy` | AIModel → Provider | inverse of `ait:develops`; ⊑ `schema:creator` | Organisation that trained the model. |
| `ait:develops` | Provider → AIModel | inverse of `ait:developedBy` | Models released by the provider. |
| `ait:supportsTask` | AITool → Task | | Task the tool can be used for. |
| `ait:inputModality` | AIModel → Modality | | Accepted input modality. |
| `ait:outputModality` | AIModel → Modality | | Produced output modality. |
| `ait:hasLicense` | AIModel → License | ⊑ `dcterms:license` | Licence of the model. |
| `ait:integratesWith` | AITool → Integration | | Platform in which the tool is available. |
| `ait:hasPricingPlan` | AITool → PricingPlan | | Plan under which the tool is offered. |
| `ait:evaluatedModel` | BenchmarkResult → AIModel | functional | Model the result belongs to. |
| `ait:onBenchmark` | BenchmarkResult → Benchmark | functional | Benchmark of the result. |
| `ait:measuresTask` | Benchmark → Task | | Task the benchmark measures. |
| `ait:derivedFrom` | AIModel → AIModel | **transitive** | Successor/derivative of an earlier model. |
| `ait:competesWith` | AITool → AITool | **symmetric, irreflexive** | Direct market competitors. |

### Datatype properties (10)

| Property | Domain → Range | Characteristics | Description |
|---|---|---|---|
| `ait:releaseDate` | AITool ⊔ AIModel → `xsd:date` | functional; ⊑ `dcterms:issued` | First public availability. |
| `ait:contextWindow` | LanguageModel → `xsd:integer` | functional | Maximum tokens per request. |
| `ait:parameterCount` | AIModel → `xsd:decimal` | functional | Parameters in billions (if published). |
| `ait:score` | BenchmarkResult → `xsd:decimal` | functional | Score in percent (0–100). |
| `ait:metric` | Benchmark → `xsd:string` | functional | Metric of the benchmark (accuracy, pass@1, …). |
| `ait:monthlyPrice` | PricingPlan → `xsd:decimal` | functional | Price per user per month, 0 = free. |
| `ait:currency` | PricingPlan → `xsd:string` | functional | ISO 4217 currency code. |
| `ait:foundedYear` | Provider → `xsd:gYear` | functional | Year the provider was founded. |
| `ait:headquartersCountry` | Provider → `xsd:string` | | Country of the headquarters. |
| `ait:spdxId` | License → `xsd:string` | functional | SPDX licence identifier. |

Names of all entities are given by `rdfs:label`; homepages by the reused `foaf:homepage`. Every
class and property of the ontology has an `rdfs:label` and an `rdfs:comment` (checked
automatically by the build script).

## 2.2 Axioms and constraints

Besides domain and range restrictions for all 25 properties, the ontology contains:

* **class hierarchy** — `LanguageModel ⊑ AIModel`, `ImageGenerationModel ⊑ AIModel`,
  `OpenLicense ⊑ License`, plus alignment of all main classes to external superclasses
  (schema.org, ML Schema, Dublin Core);
* **disjointness** — `owl:AllDisjointClasses` over the ten top-level classes (a tool cannot be a
  model, a provider cannot be a task, …) and `LanguageModel owl:disjointWith ImageGenerationModel`;
* **property characteristics** — functional properties (`providedBy`, `evaluatedModel`,
  `onBenchmark`, `releaseDate`, `score`, `monthlyPrice`, …), an inverse pair
  (`developedBy`/`develops`), a transitive property (`derivedFrom` — the lineage of a model),
  a symmetric and irreflexive property (`competesWith`);
* **union domain** — `releaseDate` is applicable to tools and models
  (`rdfs:domain [ owl:unionOf (ait:AITool ait:AIModel) ]`);
* **sub-properties** of reused vocabularies (`hasLicense ⊑ dcterms:license`,
  `releaseDate ⊑ dcterms:issued`, `providedBy ⊑ schema:provider`, `developedBy ⊑ schema:creator`).

`competesWith` is deliberately only symmetric+irreflexive and `derivedFrom` only transitive — OWL 2
DL forbids irreflexivity on transitive (non-simple) properties, so the "a model cannot be derived
from itself / from a newer model" rule is enforced by SHACL instead (shape S6).

The ontology is valid Turtle (all reused external terms are explicitly declared so that it can be loaded into Protégé as OWL 2) and is free of logical inconsistencies:
{{CONSISTENCY}}

## 2.3 Conceptual model

![Conceptual model of the AI Tools Catalogue ontology. Blue boxes are top-level classes, yellow
boxes are subclasses (dashed arrows = `rdfs:subClassOf`). Solid arrows are object properties from
domain to range; datatype properties are listed inside the classes. Characteristics:
F = functional, T = transitive, S = symmetric, I = irreflexive.](figures/ontology.png)

The diagram is generated automatically from the Turtle file (`scripts/build.py`), so it always
corresponds to the actual ontology.

## 2.4 Reuse of existing ontologies

We searched Linked Open Vocabularies (LOV), schema.org and W3C specifications for terms
covering our concepts. The most relevant candidates were:

| Vocabulary | Relevant terms | Fit |
|---|---|---|
| **schema.org** | `SoftwareApplication`, `Organization`, `Offer`, `price`, `priceCurrency`, `provider`, `creator`, `Dataset`, `isBasedOn`, `sameAs` | Very good for generic products, organisations and offers; no notion of AI models, modalities or benchmarks. |
| **W3C ML Schema (`mls:`)** | `Model`, `ModelEvaluation`, `EvaluationMeasure`, `Task`, `Implementation`, `Software` | Designed for ML experiments; models and evaluations map well. Its `Task` means an ML task (classification, regression), which is only close to our user-facing task. |
| **Dublin Core Terms** | `license`, `LicenseDocument`, `issued`, `created`, `creator`, `title` | Standard metadata; ideal for licences and dates. |
| **FOAF** | `Organization`, `homepage` | Widely used, `homepage` directly reusable. |
| **SKOS** | `Concept`, `ConceptScheme`, `broader`, `exactMatch`, `closeMatch` | Suitable for controlled lists (tasks, modalities) and for alignments. |
| **SPDX** | licence list and identifiers | Standard identifiers of licences (Apache-2.0, MIT). |
| **Wikidata** | entities for providers (OpenAI Q21708200, Google Q95, Meta Q380, GitHub Q364) | Useful for linking instances to the LOD cloud. |
| **MEX vocabulary, ML-Onto, DCAT-AP for AI** | ML experiment metadata | Too detailed (hyper-parameters, runs) or not maintained. |

**Decision.** We define our **own core classes and properties** in the `ait:` namespace and
**align** them to the external vocabularies instead of using the external terms directly.
Reasons:

1. *Precise semantics and constraints.* We need domain/range restrictions, disjointness and
   functional properties (e.g. "a tool has exactly one provider"). Asserting such axioms on
   `schema:provider` or `mls:Model` would change the meaning of terms we do not own and would
   conflict with their intentionally loose definitions (schema.org uses `domainIncludes` /
   `rangeIncludes` instead of strict domains).
2. *Missing concepts.* No vocabulary covers the distinction tool vs. model, modalities,
   context windows or pricing plans shared by several products.
3. *Interoperability is kept* via `rdfs:subClassOf` (e.g. `ait:AITool ⊑ schema:SoftwareApplication`,
   `ait:BenchmarkResult ⊑ mls:ModelEvaluation`), `rdfs:subPropertyOf`
   (`ait:hasLicense ⊑ dcterms:license`, `ait:releaseDate ⊑ dcterms:issued`) and
   `skos:closeMatch` (`ait:Task` ≈ `mls:Task`). A consumer that understands schema.org or
   Dublin Core can therefore still interpret our data after RDFS reasoning.

Some terms are **reused directly** because their semantics fits exactly and no extra constraints
are needed: `rdfs:label` (names), `foaf:homepage` (homepages), `schema:sameAs` (links of providers
to Wikidata), `schema:isBasedOn` (output of the CONSTRUCT query Q15), Dublin Core and VANN for the
ontology metadata, and SPDX identifiers as values of `ait:spdxId`.

# 3 Data

The knowledge graph (`data/ai-tools-data.ttl`) was created manually with the help of an LLM,
based on public information (vendor pricing pages, model cards and announcements) and then
reviewed. It covers 15 tools from 12 providers and 27 models, including the tools named in the
original topic (ChatGPT, Claude, Gemini, Midjourney, GitHub Copilot) and representative open-weights
models (Llama, DeepSeek, Qwen, Mistral, Gemma, gpt-oss). All classes and all properties
(except `ait:develops`, which is the inverse of `ait:developedBy` and is inferred by the reasoner)
are used in the data.

{{STATS}}

Example triples — a tool, a model and a benchmark result:

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

A second file, `data/ai-tools-data-invalid.ttl`, contains seven intentionally broken resources
used to test the SHACL shapes (Section 5).

# 4 SPARQL queries

All queries are stored in the `queries/` directory and were executed with RDFLib over the union of
the ontology and the data (the ontology is needed for `rdfs:subClassOf*` paths). Results below are
produced automatically by the build script. The following prefixes are declared in every query
file and are omitted from the listings below for brevity:

```sparql
PREFIX ait:  <https://otavlna.github.io/4iz444-ai-tools-kg/ontology#>
PREFIX aid:  <https://otavlna.github.io/4iz444-ai-tools-kg/data/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
```

## CQ1 — Coding tools available in Visual Studio Code

A simple conjunctive query combining a task, an integration and a property path
(`ait:providedBy/rdfs:label`) to the provider's name.

{{QUERY:cq01}}

{{RESULT:cq01}}

Four tools satisfy both conditions. Cursor is not listed because it is a stand-alone editor (a
desktop application) rather than a VS Code extension, and chat assistants such as ChatGPT
generate code but do not integrate into the IDE.

## CQ2 — Models with image input and text output

The class is matched with `a/rdfs:subClassOf* ait:AIModel`, so the query works for instances of
any subclass. `OPTIONAL` + `COUNT(DISTINCT)` adds the number of tools using the model (0 for
models that are in the graph only as predecessors).

{{QUERY:cq02}}

{{RESULT:cq02}}

Multimodal input has become the norm: 16 of the 22 language models accept images. The most
widely used ones are the current flagships of the three big labs (Claude Sonnet 4.5, GPT-5,
Gemini 2.5 Pro), each used in five tools — their own and those of third parties.

## CQ3 — Average price of paid plans per provider

Because one plan can be linked to several tools of the same provider, the inner sub-query first
selects `DISTINCT` (provider, plan) pairs; the outer query aggregates with `COUNT`, `AVG`, `MIN`
and `MAX` and rounds the average to two decimals.

{{QUERY:cq03}}

{{RESULT:cq03}}

The averages are dominated by premium tiers: Perplexity, Google, Anysphere (Cursor) and OpenAI
each have a 200–250 USD tier, while the entry-level paid tier is almost universally 20 USD.
GitHub has the lowest average price of paid plans (22.67 USD) and shares the cheapest entry tier
(10 USD) with Midjourney. Le Chat is priced in EUR, which is why the
currency is part of the grouping — averaging prices in different currencies would be meaningless.

## CQ4 — Best open-weights models on MMLU

The licence is matched by its class (`a ait:OpenLicense`), the benchmark result is joined
through the n-ary `BenchmarkResult` node.

{{QUERY:cq04}}

{{RESULT:cq04}}

Openly licensed models reach the level of closed models on MMLU (GPT-4.1: 90.2, GPT-4o: 88.7).
Model size helps but is not decisive: the 117B gpt-oss-120b scores nearly as well as the 671B
DeepSeek-R1, and the small Mistral Small 3.1 (24B) and Gemma 3 (27B) are only ~10 points behind
models fifteen times larger.

## CQ5 — Number of tools per task

`GROUP BY` with `COUNT` and `GROUP_CONCAT`; the sub-query with `ORDER BY` makes the
concatenated lists alphabetical and the results reproducible.

{{QUERY:cq05}}

{{RESULT:cq05}}

Code generation is the most common capability (12 of 15 tools) — practically every
general-purpose assistant can write code. Only specialised coding tools offer code review and
inline code completion. The task *Knowledge and reasoning* does not appear because it is used only
to classify benchmarks, not tools.

## CQ6 — Tools built on models of other providers

The key condition is `FILTER (?tp != ?mp)`: the provider of the tool differs from the developer
of the model.

{{QUERY:cq06}}

{{RESULT:cq06}}

Four tools are pure "aggregators" without in-house models. GitHub Copilot, Cursor and Perplexity
all depend on the same three labs (OpenAI, Anthropic, Google), which illustrates how concentrated
the model layer of the market is. Ollama, a tool for running models locally, depends on six
providers, all of them publishing open weights.

## CQ7 — Model lineage

The transitive relation `ait:derivedFrom` is followed with the property path `ait:derivedFrom+`.
The difference of two `xsd:date` values is an `xsd:duration` (e.g. `P130D`), from which the number
of days is extracted with `REPLACE` and cast to an integer.

{{QUERY:cq07}}

{{RESULT:cq07}}

The data assert only direct predecessors (Sonnet 4.5 → Sonnet 4 → 3.7 Sonnet → 3.5 Sonnet), but
the property path returns the whole chain. Both labs release a new flagship generation roughly
every 4 months (113–130 days between GPT-5 and o3/GPT-4.1 and between Claude Sonnet 4.5 and
Sonnet 4).

## CQ8 — Largest context window per provider

A sub-query computes the maximum per provider; it is joined back to the models to find which
model(s) reach it. Ties are aggregated with `GROUP_CONCAT`.

{{QUERY:cq08}}

{{RESULT:cq08}}

Google, OpenAI (GPT-4.1) and Meta (Llama 4 Maverick) offer context windows of about one million
tokens. All Anthropic models in the graph share the same 200k window, so five models tie for the
maximum.

## CQ9 — Providers offering both text and image generation

Two independent tool patterns for the same provider (`?t1`, `?t2`) express "the provider offers
both"; an `OPTIONAL` block looks for an image model developed by the same provider.

{{QUERY:cq09}}

{{RESULT:cq09}}

OpenAI and Google cover both tasks with their own image models (gpt-image-1, Imagen 4). Meta AI
also generates images, but no Meta image model is part of the graph — the query reveals a gap in
the data that could be filled in a next version. Midjourney is not listed because it only
generates images.

## CQ10 — Free tools running on openly licensed models

Joins tools, pricing plans with price 0 and models whose licence is an `ait:OpenLicense`.

{{QUERY:cq10}}

{{RESULT:cq10}}

Five tools can be used free of charge with an open-weights model. Ollama stands out with six such
models, because it runs them locally on the user's hardware; DeepSeek Chat, Meta AI and Qwen Chat
are hosted chat applications of providers that publish the weights of their models.

## Q11 — Providers' best scores compared with the benchmark average

An analytical query with two levels of aggregation: the sub-query computes the average score
per benchmark (only benchmarks with at least 5 results are considered), the outer query takes
the best (`MAX`) model of each provider and computes the difference to the average.

{{QUERY:q11}}

{{RESULT:q11}}

The spread is largest on the agentic coding benchmark SWE-bench Verified, where Anthropic's
best model is 12.7 points above the average and DeepSeek 15.3 points below it. On the older
MMLU, the results are saturated — the best models of five providers are within 4 points of the
average, and only the smaller models (Mistral Small 3.1, Gemma 3 27B) fall clearly behind.

## Q12 — Analysis of model names (string functions)

Uses `REGEX`, `REPLACE` with a capturing group, `STRBEFORE` and `UCASE` to split names such as
"Claude Sonnet 4.5" into a family ("CLAUDE SONNET") and a version ("4.5"), and then aggregates
releases per family with `HAVING (COUNT(?m) > 1)`.

{{QUERY:q12}}

{{RESULT:q12}}

The query recovers model families purely from naming conventions. It also uncovers a change of
naming scheme: Anthropic's "Claude 3.5 Sonnet" / "Claude 3.7 Sonnet" became "Claude Sonnet 4" /
"Claude Sonnet 4.5", so the string analysis splits one product line into two families — the
explicit `ait:derivedFrom` relation (CQ7) is the more reliable way to express lineage.

## Q13 — Competitor network (symmetric property, EXISTS)

The relation `competesWith` is declared symmetric but is stated only in one direction in the
data; the alternative path `ait:competesWith|^ait:competesWith` follows both directions without
reasoning. `EXISTS` inside `IF` tests whether two competitors share an underlying model.

{{QUERY:q13}}

{{RESULT:q13}}

ChatGPT has the most direct competitors. In the coding segment (Copilot, Cursor, Claude Code,
Codex) competitors almost always share models — they compete on the product, not on the model.
In the chat segment, competitors mostly use their own models (Claude, Le Chat, DeepSeek Chat share
none with their competitors).

## Q14 — Models used in tools but lacking benchmark results (negation)

`FILTER NOT EXISTS` finds language models that are used by at least one tool but have no
`BenchmarkResult` — a data-quality / data-gap check.

{{QUERY:q14}}

{{RESULT:q14}}

Two models in production use lack benchmark data in the graph and are candidates for the next
data update.

## Q15 — CONSTRUCT: materialising tool dependencies

A `CONSTRUCT` query derives new knowledge: a direct link `schema:isBasedOn` from a tool to every
external provider whose model it uses. The resulting graph (stored in
`results/q15-construct-tool-dependency.ttl`) could be added to the knowledge graph to answer
dependency questions without the two-step path.

{{QUERY:q15}}

{{RESULT:q15}}

# 5 SHACL validation

The shapes are in `shacl/shapes.ttl` and were validated with pySHACL. Six node shapes cover all
main classes; one of them uses a SPARQL-based constraint.

## S1 AIToolShape

Every tool has a name (`xsd:string`), exactly one provider (`sh:minCount 1` + `sh:maxCount 1`,
value of class `ait:Provider`), at least one model of class `ait:AIModel`, at least one task and at
least one pricing plan.

{{SHAPE:AIToolShape}}

## S2 AIModelShape

Every model has exactly one developer, exactly one release date of datatype `xsd:date`, exactly one
licence and at least one input and output modality. The context window and parameter count are
optional, but when present they must be single positive numbers of the right datatype
(`sh:minExclusive 0`).

{{SHAPE:AIModelShape}}

## S3 LanguageModelShape and ImageGenerationModelShape

Subclass-specific rules: a language model must state its context window and must output text
(`sh:hasValue aid:Text`); an image generation model must output images.

{{SHAPE:LanguageModelShape}}

{{SHAPE:ImageGenerationModelShape}}

## S4 BenchmarkResultShape

Every result refers to exactly one model and one benchmark and has exactly one decimal score in
the interval [0, 100] (`sh:minInclusive`, `sh:maxInclusive`).

{{SHAPE:BenchmarkResultShape}}

## S5 PricingPlanShape

Every plan has a name and exactly one non-negative decimal price; the currency must be one of the
supported codes (`sh:in ("USD" "EUR")`).

{{SHAPE:PricingPlanShape}}

## S6 ModelLineageShape (SPARQL constraint)

A model cannot have been released before a model it is derived from. This temporal rule compares
values of two different nodes and cannot be expressed with core SHACL constraints, so a
`sh:SPARQLConstraint` is used; every row returned by the `SELECT` is a violation.

{{SHAPE:ModelLineageShape}}

## 5.1 Validation results

**Valid knowledge graph** (`data/ai-tools-data.ttl`):

{{SHACL_VALID}}

**Knowledge graph + intentionally invalid data** (`data/ai-tools-data-invalid.ttl`). The file
contains a tool without a provider and pricing plan, a tool "powered by" a provider instead of a
model, a model with a string release date, a negative context window, no licence and audio-only
output, an image model producing only text, a benchmark result with a score of 112.5 and no
benchmark, a plan with a negative price in CZK, and a model released before its predecessor:

{{SHACL_INVALID}}

Every intentionally introduced error was detected by the expected shape and constraint
component, and the valid data conform to all shapes, which shows that the shapes are neither too
weak nor too strict for the real data.

# 6 Conclusion

We designed an ontology with 13 classes, 25 properties and a range of OWL axioms for a catalogue
of AI tools, populated it with a knowledge graph of almost 1,000 triples, answered ten competency
questions and five additional analytical queries in SPARQL, and validated the data with six SHACL
shapes. The most valuable modelling decisions were the separation of tools from models and the
modelling of benchmark results and pricing plans as separate nodes — they enable the most
interesting analyses (dependencies between providers, price comparisons, comparison with
benchmark averages).

**Limitations and future work.** The data are a manually created snapshot and will age quickly;
benchmark scores are vendor-reported under different settings. A natural next step would be to
populate the graph automatically from structured sources (e.g. Hugging Face model cards, Wikidata,
public leaderboards) using YARRRML/RML mappings, to add API pricing per token, and to extend the
`Task` concept into a SKOS hierarchy (e.g. *code completion* ⊑ *code generation*).

# Appendix A — Repository and reproducibility

All files are available at <https://github.com/otavlna/4iz444-ai-tools-kg>:

| Path | Content |
|---|---|
| `ontology/ai-tools.ttl` | ontology (OWL 2, Turtle) |
| `data/ai-tools-data.ttl` | knowledge graph |
| `data/ai-tools-data-invalid.ttl` | intentionally invalid data for SHACL testing |
| `queries/*.rq` | SPARQL queries CQ1–CQ10, Q11–Q15 |
| `shacl/shapes.ttl` | SHACL shapes |
| `results/` | query results (CSV, Markdown, Turtle) and SHACL reports |
| `scripts/build.py` | build pipeline (parsing, reasoning, queries, SHACL, diagram, report) |

Running `make all` re-creates all results, the diagram and this report from the source files.
