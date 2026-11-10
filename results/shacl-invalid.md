**Conforms:** `false` — 13 violation(s).

| Focus node | Shape | Path | Constraint | Message |
|---|---|---|---|---|
| aid:BadModel_NoImage | aish:ImageGenerationModelShape | ait:outputModality | sh:HasValueConstraintComponent | An image generation model must produce image output. |
| aid:BadModel_TimeTravel | aish:ModelLineageShape | (SPARQL) | sh:SPARQLConstraintComponent | Model aid:BadModel_TimeTravel (released 2024-01-01) is derived from aid:ClaudeSonnet45, which was released later (2025-09-29). |
| aid:BadModel_Types | aish:AIModelShape | ait:contextWindow | sh:MinExclusiveConstraintComponent | The context window must be a single positive integer (number of tokens). |
| aid:BadModel_Types | aish:AIModelShape | ait:hasLicense | sh:MinCountConstraintComponent | An AI model must have exactly one licence. |
| aid:BadModel_Types | aish:AIModelShape | ait:releaseDate | sh:DatatypeConstraintComponent | An AI model must have exactly one release date of type xsd:date. |
| aid:BadModel_Types | aish:LanguageModelShape | ait:outputModality | sh:HasValueConstraintComponent | A language model must produce text output. |
| aid:BadPlan_Price | aish:PricingPlanShape | ait:currency | sh:InConstraintComponent | The currency must be one of the supported ISO 4217 codes: USD, EUR. |
| aid:BadPlan_Price | aish:PricingPlanShape | ait:monthlyPrice | sh:MinInclusiveConstraintComponent | A pricing plan must have exactly one non-negative monthly price (xsd:decimal). |
| aid:BadResult_Score | aish:BenchmarkResultShape | ait:onBenchmark | sh:MinCountConstraintComponent | A benchmark result must refer to exactly one benchmark. |
| aid:BadResult_Score | aish:BenchmarkResultShape | ait:score | sh:MaxInclusiveConstraintComponent | A benchmark score must be a single decimal between 0 and 100. |
| aid:BadTool_NoProvider | aish:AIToolShape | ait:hasPricingPlan | sh:MinCountConstraintComponent | An AI tool must have at least one pricing plan. |
| aid:BadTool_NoProvider | aish:AIToolShape | ait:providedBy | sh:MinCountConstraintComponent | An AI tool must have exactly one provider of type ait:Provider. |
| aid:BadTool_WrongModel | aish:AIToolShape | ait:poweredBy | sh:ClassConstraintComponent | An AI tool must be powered by at least one ait:AIModel. |
