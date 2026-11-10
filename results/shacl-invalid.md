**Conforms:** `false` — 20 violation(s).

| Focus node | Shape | Path | Constraint | Message |
|---|---|---|---|---|
| BadBenchmark | S8 | ait:measuresTask | sh:MinCount | A benchmark must measure at least one ait:Task. |
| BadBenchmark | S8 | ait:metric | sh:MinCount | A benchmark must state exactly one metric. |
| BadLicense | S7 | ait:spdxId | sh:Pattern | A licence must have exactly one valid SPDX identifier (e.g. 'Apache-2.0' or 'LicenseRef-Proprietary'). |
| BadModel_NoImage | S3 | ait:outputModality | sh:HasValue | An image generation model must produce image output. |
| BadModel_TimeTravel | S10 | (SPARQL) | sh:SPARQL | Model aid:BadModel_TimeTravel (released 2024-01-01) is derived from aid:ClaudeSonnet45, which was released later (2025-09-29). |
| BadModel_Types | S2 | ait:contextWindow | sh:MinExclusive | The context window must be a single positive integer (number of tokens). |
| BadModel_Types | S2 | ait:hasLicense | sh:MinCount | An AI model must have exactly one licence. |
| BadModel_Types | S2 | ait:releaseDate | sh:Datatype | An AI model must have exactly one release date of type xsd:date. |
| BadModel_Types | S3 | ait:outputModality | sh:HasValue | A language model must produce text output. |
| BadPlan_Price | S5 | ait:currency | sh:In | The currency must be one of the supported ISO 4217 codes: USD, EUR. |
| BadPlan_Price | S5 | ait:monthlyPrice | sh:MinInclusive | A pricing plan must have exactly one non-negative monthly price (xsd:decimal). |
| BadProvider | S6 | ait:foundedYear | sh:Datatype | The founding year must be a single value of type xsd:gYear. |
| BadProvider | S6 | ait:headquartersCountry | sh:MinCount | A provider must state its headquarters country. |
| BadProvider | S6 | foaf:homepage | sh:NodeKind | A homepage must be an IRI, not a literal. |
| BadResult_Score | S4 | ait:onBenchmark | sh:MinCount | A benchmark result must refer to exactly one benchmark. |
| BadResult_Score | S4 | ait:score | sh:MaxInclusive | A benchmark score must be a single decimal between 0 and 100. |
| BadTask | S9 | rdfs:label | sh:MaxCount | A task, modality or integration must have exactly one name. |
| BadTool_NoProvider | S1 | ait:hasPricingPlan | sh:MinCount | An AI tool must have at least one pricing plan. |
| BadTool_NoProvider | S1 | ait:providedBy | sh:MinCount | An AI tool must have exactly one provider of type ait:Provider. |
| BadTool_WrongModel | S1 | ait:poweredBy | sh:Class | An AI tool must be powered by at least one ait:AIModel. |
