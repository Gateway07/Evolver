# OpenEvolve L1 — Round 1 Output (H1/H2 using a richer surrogate index model + evaluator WHERE-suffix)

This is an **illustrative first-round** L1 output that:
- invents a **richer surrogate model** (stop-words + tokenization + prefix-4 DF tables) in an **immutable theory schema**;
- tests **H1/H2 empirically** via the evaluator using **WHERE-suffix predicates** (boolean expressions over `osmand.address a`);
- returns **Experiment (Reality)** hypotheses in `hypothesis_dsl` (per `hypothesis.schema.json`) and **Mechanism (Theory)** in `theory_dsl` (per `theory.schema.json`).
- leaves **signatures as placeholders** (wrapper computes `sha256(canonical_json/sql)`).

---

## 0) Key idea of the richer approximation (surrogate index)
OsmAnd-like behavior approximated by:
- tokenization + normalization of street names
- stop-word removal
- prefix-4 indexing per token position
- document-frequency stats:
  - `df_head` (frequency of prefix4 at token position 1)
  - `min_tail_df` (minimum df among tail tokens, pos > 1)

### Group definitions to test
- **H1 treatment group**: *Frequent head prefix + rare tail prefix*  
  (high candidate collisions at head + unusually discriminative tail) — hypothesized to trigger runtime pruning/heuristics that can drop correct matches ⇒ higher NotFound.
- **H2 treatment group**: *Frequent head prefix + common tail prefix*  
  (high collision head but tail not rare) — hypothesized to be more stable/less error-prone than H1.

Both are compared against a **fixed stratified control** (by `city_id`) under a strict split protocol.

---

## 1) Output JSON (Round 1)

~~~json
{
  "iteration": {
    "id": "l1_round_0001",
    "timestamp_utc": "2026-01-07T11:15:00Z",
    "locale": "en_US",
    "notes": "Round 1: build surrogate prefix4 index in a theory schema; test H1/H2 via evaluator using EXISTS(...) WHERE-suffix predicates; collect initial tracing evidence."
  },

  "experiment": {
    "hypotheses": [
      {
        "hypothesis_dsl": {
          "schema_version": "1.0",
          "hypothesis_id": "H1_head_frequent_tail_rare",
          "type": "DIFF_RATE",
          "axioms": ["A0", "A1", "A2", "A3"],

          "scope": {
            "app_version": "{APP_VERSION}",
            "index_build_id": "{INDEX_BUILD_ID}",
            "locale": "en_US",
            "notes": "H1: compare frequent head + rare tail group vs fixed stratified control. Groups are defined over osmand.address a and the surrogate theory schema views."
          },

          "feature_family": "prefix4_head_tail_df",
          "metric": "notFoundRate",

          "groups": [
            {
              "name": "G_H1_head_frequent_tail_rare",
              "definition": "where_sql",
              "group_sql": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id = h.id WHERE h.id = a.street_id AND h.df_head >= 400 AND t.min_tail_df <= 5 )",
              "group_signature": "{GROUP_SIG_SHA256_PLACEHOLDER}",
              "implies": [],
              "notes": "Frequent head prefix (df_head high) + rare tail prefix (min_tail_df low)."
            },
            {
              "name": "G_control_stratified_random",
              "definition": "stratified_random_sample",
              "params": {
                "stratify_by": ["city_id"],
                "per_stratum_n": 50,
                "seed": 1337
              },
              "notes": "Control is wrapper-materialized into a concrete WHERE-suffix OR applied as protocol outside L1. L1 must not optimize control selection."
            }
          ],

          "group_roles": {
            "treatment": "G_H1_head_frequent_tail_rare",
            "control": "G_control_stratified_random"
          },

          "stratification": {
            "stratify_by": ["city_id"],
            "split_policy": {
              "method": "by_state_country",
              "training": { "states": ["{TRAIN_STATE_*}"], "countries": ["{TRAIN_COUNTRY_*}"] },
              "validation": { "states": ["{VAL_STATE_*}"], "countries": ["{VAL_COUNTRY_*}"] },
              "holdout": { "states": ["{HOLDOUT_STATE_*}"], "countries": ["{HOLDOUT_COUNTRY_*}"] }
            },
            "control_protocol": {
              "control_group_name": "G_control_stratified_random",
              "per_stratum_n": 50,
              "seed": 1337
            }
          },

          "claim": {
            "compare": { "group_a": "G_H1_head_frequent_tail_rare", "group_b": "G_control_stratified_random" },
            "delta_min": 0.08,
            "confidence_level": 0.95,
            "notes": "Expect a material NotFoundRate increase for frequent-head + rare-tail streets vs control."
          },

          "evaluation": {
            "effect_size": {
              "type": "difference_of_proportions",
              "definition": "Δ = pA - pB, where p = notFoundRate"
            },
            "ci": {
              "method": "bootstrap_by_strata",
              "bootstrap": { "resamples": 2000, "seed": 20260107 },
              "notes": "Bootstrap within city_id strata."
            },
            "reproducibility": {
              "repeat_runs": 3,
              "accept_if_ci_supports_claim": true,
              "notes": "Repeat evaluator runs 3x (same group_sql and control protocol) and accept only if CI consistently supports Δ >= delta_min."
            },
            "acceptance_gate": {
              "require_novelty": true,
              "novelty_kind": ["reason_family", "feature_bin"],
              "notes": "Must produce new/expanded res_error clusters and/or a new feature-bin region (df_head high & min_tail_df low)."
            }
          },

          "expected_effect": {
            "direction": "increase",
            "min_effect_size": 0.08,
            "notes": "Hypothesis-level expectation; final decision relies on CI + reproducibility."
          },

          "signatures": {
            "hypothesis_signature": "{HYP_SIG_SHA256_PLACEHOLDER}"
          }
        }
      },

      {
        "hypothesis_dsl": {
          "schema_version": "1.0",
          "hypothesis_id": "H2_head_frequent_tail_common",
          "type": "DIFF_RATE",
          "axioms": ["A0", "A1", "A2", "A3"],

          "scope": {
            "app_version": "{APP_VERSION}",
            "index_build_id": "{INDEX_BUILD_ID}",
            "locale": "en_US",
            "notes": "H2: compare frequent head + common tail group vs fixed stratified control. Intended as contrast/sanity check against H1."
          },

          "feature_family": "prefix4_head_tail_df",
          "metric": "notFoundRate",

          "groups": [
            {
              "name": "G_H2_head_frequent_tail_common",
              "definition": "where_sql",
              "group_sql": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id = h.id WHERE h.id = a.street_id AND h.df_head >= 400 AND t.min_tail_df >= 200 )",
              "group_signature": "{GROUP_SIG_SHA256_PLACEHOLDER}",
              "implies": [],
              "notes": "Frequent head prefix (df_head high) + common tail prefix (min_tail_df high)."
            },
            {
              "name": "G_control_stratified_random",
              "definition": "stratified_random_sample",
              "params": {
                "stratify_by": ["city_id"],
                "per_stratum_n": 50,
                "seed": 1337
              }
            }
          ],

          "group_roles": {
            "treatment": "G_H2_head_frequent_tail_common",
            "control": "G_control_stratified_random"
          },

          "stratification": {
            "stratify_by": ["city_id"],
            "split_policy": {
              "method": "by_state_country",
              "training": { "states": ["{TRAIN_STATE_*}"], "countries": ["{TRAIN_COUNTRY_*}"] },
              "validation": { "states": ["{VAL_STATE_*}"], "countries": ["{VAL_COUNTRY_*}"] },
              "holdout": { "states": ["{HOLDOUT_STATE_*}"], "countries": ["{HOLDOUT_COUNTRY_*}"] }
            },
            "control_protocol": {
              "control_group_name": "G_control_stratified_random",
              "per_stratum_n": 50,
              "seed": 1337
            }
          },

          "claim": {
            "compare": { "group_a": "G_H2_head_frequent_tail_common", "group_b": "G_control_stratified_random" },
            "delta_max": 0.02,
            "confidence_level": 0.95,
            "notes": "Expect no large NotFoundRate increase vs control for common-tail case."
          },

          "evaluation": {
            "effect_size": {
              "type": "difference_of_proportions",
              "definition": "Δ = pA - pB, where p = notFoundRate"
            },
            "ci": {
              "method": "bootstrap_by_strata",
              "bootstrap": { "resamples": 2000, "seed": 20260107 }
            },
            "reproducibility": {
              "repeat_runs": 3,
              "accept_if_ci_supports_claim": true,
              "notes": "Repeat evaluator runs 3x. Accept if CI supports Δ <= delta_max."
            },
            "acceptance_gate": {
              "require_novelty": false,
              "notes": "Contrast hypothesis; novelty not required."
            }
          },

          "expected_effect": {
            "direction": "no_change",
            "min_effect_size": 0.0
          },

          "signatures": {
            "hypothesis_signature": "{HYP_SIG_SHA256_PLACEHOLDER}"
          }
        }
      }
    ],

    "empirical_runs_round1": {
      "notes": "Round-1 single-run measurements shown for illustration. Reproducibility requires repeat_runs=3 per hypothesis and control.",
      "evaluator_endpoint": "http://localhost:8080/admin/search-test/search-by-sql",
      "curl_get_with_body_example": "curl -i -X GET \"http://localhost:8080/admin/search-test/search-by-sql\" --data-binary \"<WHERE_SUFFIX>\"",
      "runs": [
        {
          "group_name": "G_H1_head_frequent_tail_rare",
          "run_id": 21001,
          "where_suffix_sent": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id = h.id WHERE h.id = a.street_id AND h.df_head >= 400 AND t.min_tail_df <= 5 )",
          "aggregates": {
            "status": "COMPLETED",
            "totalCount": 6000,
            "failedCount": 60,
            "foundCount": 4800,
            "partialFoundCount": 240,
            "totalDurationMs": 110000,
            "searchDurationMs": 104000,
            "totalBytes": 14500000
          },
          "derived": {
            "notFoundCount": 900,
            "notFoundRate": 0.15
          }
        },
        {
          "group_name": "G_control_stratified_random",
          "run_id": 21002,
          "where_suffix_sent": "{CONTROL_WHERE_SUFFIX_MATERIALIZED_BY_WRAPPER}",
          "aggregates": {
            "status": "COMPLETED",
            "totalCount": 6000,
            "failedCount": 45,
            "foundCount": 5400,
            "partialFoundCount": 210,
            "totalDurationMs": 88000,
            "searchDurationMs": 82000,
            "totalBytes": 11800000
          },
          "derived": {
            "notFoundCount": 345,
            "notFoundRate": 0.0575
          }
        },
        {
          "group_name": "G_H2_head_frequent_tail_common",
          "run_id": 21003,
          "where_suffix_sent": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id = h.id WHERE h.id = a.street_id AND h.df_head >= 400 AND t.min_tail_df >= 200 )",
          "aggregates": {
            "status": "COMPLETED",
            "totalCount": 6000,
            "failedCount": 40,
            "foundCount": 5320,
            "partialFoundCount": 220,
            "totalDurationMs": 90000,
            "searchDurationMs": 83500,
            "totalBytes": 12000000
          },
          "derived": {
            "notFoundCount": 420,
            "notFoundRate": 0.07
          }
        }
      ],
      "effect_size_snapshot": {
        "H1_vs_control": {
          "pA": 0.15,
          "pB": 0.0575,
          "delta": 0.0925,
          "ci_95": ["{CI_LOW_PLACEHOLDER}", "{CI_HIGH_PLACEHOLDER}"],
          "status": "PROMISING_PENDING_REPEATS"
        },
        "H2_vs_control": {
          "pA": 0.07,
          "pB": 0.0575,
          "delta": 0.0125,
          "ci_95": ["{CI_LOW_PLACEHOLDER}", "{CI_HIGH_PLACEHOLDER}"],
          "status": "CONSISTENT_WITH_SMALL_DELTA_PENDING_REPEATS"
        }
      }
    }
  },

  "theory": {
    "theory_dsl": {
      "schema_version": "1.0",

      "theory_id": "M_prefix4_stopwords_head_tail_df",
      "theory_name": "prefix4_head_tail_df",
      "theory_type": "PIPELINE_MODEL",

      "axioms": ["A0", "A1", "A2", "A3"],

      "scope": {
        "locale": "en_US",
        "dataset": {
          "source": "postgres",
          "address_view": "osmand.address"
        },
        "split_policy": {
          "method": "by_state_country",
          "training": { "states": ["{TRAIN_STATE_*}"], "countries": ["{TRAIN_COUNTRY_*}"] },
          "validation": { "states": ["{VAL_STATE_*}"], "countries": ["{VAL_COUNTRY_*}"] },
          "holdout": { "states": ["{HOLDOUT_STATE_*}"], "countries": ["{HOLDOUT_COUNTRY_*}"] }
        },
        "notes": "Mechanism: frequent head prefix causes candidate explosion; rare tail token + pruning/topN heuristics can lead to missing correct match (NotFound)."
      },

      "inputs": [
        { "name": "street_id", "source": "a.street_id", "type": "int" },
        { "name": "street_name", "source": "a.street_name", "type": "string" },
        { "name": "city_id", "source": "a.city_id", "type": "int" }
      ],

      "features": {
        "df_head": {
          "expr": "(SELECT df_head FROM {THEORY_SCHEMA}.street_head_df h WHERE h.id = a.street_id)",
          "type": "int",
          "notes": "Head prefix4 document frequency (token position 1)."
        },
        "min_tail_df": {
          "expr": "(SELECT min_tail_df FROM {THEORY_SCHEMA}.street_tail_min_df t WHERE t.id = a.street_id)",
          "type": "int",
          "notes": "Minimum tail prefix4 df across pos>1 tokens."
        },
        "collision_risk": {
          "expr": "LN(1 + df_head)",
          "type": "float",
          "notes": "Proxy for candidate explosion due to frequent head prefix."
        },
        "disambiguation_strength": {
          "expr": "1.0 / (1.0 + min_tail_df)",
          "type": "float",
          "notes": "Proxy: rare tail token may be strong disambiguator but can be underweighted/filtered in runtime heuristics."
        },
        "risk_score": {
          "expr": "{W1}*collision_risk + {W2}*disambiguation_strength",
          "type": "float",
          "notes": "Minimal interpretable risk score; refined once tracing confirms pruning behavior."
        }
      },

      "model": {
        "outputs": ["risk_score", "predict_notfound", "predict_reason_family", "candidate_count_est"],
        "logic": [
          { "id": "s1", "kind": "assign", "assign": { "target": "df_head", "expr": "df_head" } },
          { "id": "s2", "kind": "assign", "assign": { "target": "min_tail_df", "expr": "min_tail_df" } },
          { "id": "s3", "kind": "assign", "assign": { "target": "candidate_count_est", "expr": "df_head" } },
          { "id": "s4", "kind": "assign", "assign": { "target": "risk_score", "expr": "risk_score" } },
          {
            "id": "s5",
            "kind": "rule",
            "rule": {
              "if": "df_head >= 400 AND min_tail_df <= 5 AND risk_score > {T}",
              "then": { "predict_notfound": true, "predict_reason_family": "COLLISION_PRUNE_TAIL_UNDERWEIGHT" },
              "else": { "predict_notfound": false, "predict_reason_family": "OTHER" }
            }
          }
        ],
        "parameters": { "W1": 1.0, "W2": 120.0, "T": "{RISK_THRESHOLD_T}" },
        "complexity": { "num_features": 5, "num_steps": 5, "description": "Small pipeline model aligned to surrogate DF stats and traced runtime pruning." }
      },

      "predictions": {
        "monotonicity": [
          { "feature": "df_head", "direction": "increases", "target": "candidate_count_est", "notes": "More frequent head prefix implies more candidates." },
          { "feature": "risk_score", "direction": "increases", "target": "predict_notfound", "notes": "Higher risk score implies higher NotFound likelihood." }
        ],
        "reason_mapping": [
          { "when": "df_head >= 400 AND min_tail_df <= 5", "reason_family": "COLLISION_PRUNE_TAIL_UNDERWEIGHT", "notes": "High head collision + rare tail indicates pruning/heuristic mismatch." }
        ],
        "notes": "Round-1 mechanism derived from surrogate index structure; requires traced variable alignment and holdout scoring."
      },

      "validation": {
        "protocol": {
          "holdout_control_sample": {
            "stratify_by": ["city_id"],
            "per_stratum_n": 50,
            "seed": 1337,
            "notes": "Fixed scoring-only holdout sample."
          },
          "holdout_feature_bins": [
            { "name": "bin_head_high_tail_rare", "where_sql": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id=h.id WHERE h.id=a.street_id AND h.df_head>=400 AND t.min_tail_df<=5 )" },
            { "name": "bin_head_high_tail_common", "where_sql": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id=h.id WHERE h.id=a.street_id AND h.df_head>=400 AND t.min_tail_df>=200 )" }
          ],
          "no_active_search_on_holdout": true
        },
        "metrics": ["AUC", "topk_lift"],
        "acceptance": {
          "must_generalize": true,
          "min_auc": "{MIN_AUC_PLACEHOLDER}",
          "max_complexity": { "num_features": 8, "num_steps": 16 },
          "notes": "Must show predictive lift on HOLDOUT and remain interpretable. Must also satisfy tracing alignment (runtime variable correlation)."
        }
      },

      "db_materialization": {
        "policy": "VIEWS_ONLY",
        "theory_schema_name": "{THEORY_SCHEMA}",
        "manifest_sql": "-- Immutable surrogate index build (PostgreSQL)\n-- Schema name is versioned & signature-derived by wrapper.\n\nCREATE SCHEMA IF NOT EXISTS {THEORY_SCHEMA};\n\n-- Stop words are stored in osmand.stop_word (assumed pre-existing, curated).\nCREATE VIEW {THEORY_SCHEMA}.stop_word AS\nSELECT name FROM osmand.stop_word;\n\n-- Normalize streets (lowercased, punctuation -> spaces)\nCREATE VIEW {THEORY_SCHEMA}.street_norm AS\nSELECT s.id,\n       LOWER(TRIM(REGEXP_REPLACE(s.name, '[-\\.,/]+', ' ', 'g'))) AS norm_name\nFROM osmand.street s;\n\n-- Tokenize streets into (id, pos, word)\nCREATE VIEW {THEORY_SCHEMA}.street_word AS\nSELECT n.id,\n       t.pos,\n       t.word\nFROM {THEORY_SCHEMA}.street_norm n\nCROSS JOIN LATERAL (\n  SELECT row_number() OVER () AS pos,\n         w AS word\n  FROM unnest(regexp_split_to_array(n.norm_name, '\\\\s+')) AS w\n) t\nWHERE t.word <> '';\n\n-- Prefix-4 tokens excluding stop words\nCREATE VIEW {THEORY_SCHEMA}.street_p4 AS\nSELECT id,\n       pos,\n       LEFT(word || '    ', 4) AS p4\nFROM {THEORY_SCHEMA}.street_word\nWHERE word NOT IN (SELECT name FROM {THEORY_SCHEMA}.stop_word);\n\n-- Document frequency of prefix4 across all positions\nCREATE VIEW {THEORY_SCHEMA}.p4_df AS\nSELECT p4, COUNT(DISTINCT id) AS df\nFROM {THEORY_SCHEMA}.street_p4\nGROUP BY p4;\n\n-- Document frequency of prefix4 for head token only (pos=1)\nCREATE VIEW {THEORY_SCHEMA}.p4_head_df AS\nSELECT p4, COUNT(DISTINCT id) AS df_head\nFROM {THEORY_SCHEMA}.street_p4\nWHERE pos = 1\nGROUP BY p4;\n\n-- Per-street head df\nCREATE VIEW {THEORY_SCHEMA}.street_head_df AS\nSELECT sp.id,\n       sp.p4 AS p4_head,\n       hd.df_head\nFROM {THEORY_SCHEMA}.street_p4 sp\nJOIN {THEORY_SCHEMA}.p4_head_df hd ON hd.p4 = sp.p4\nWHERE sp.pos = 1;\n\n-- Per-street minimum tail df (pos>1)\nCREATE VIEW {THEORY_SCHEMA}.street_tail_min_df AS\nSELECT sp.id,\n       MIN(d.df) AS min_tail_df\nFROM {THEORY_SCHEMA}.street_p4 sp\nJOIN {THEORY_SCHEMA}.p4_df d ON d.p4 = sp.p4\nWHERE sp.pos > 1\nGROUP BY sp.id;\n",
        "objects": [
          { "name": "stop_word", "kind": "VIEW", "depends_on": ["osmand.stop_word"], "notes": "Curated stop words; treated as stable input." },
          { "name": "street_norm", "kind": "VIEW", "depends_on": ["osmand.street"], "notes": "Normalization uses regexp replace." },
          { "name": "street_word", "kind": "VIEW", "depends_on": ["street_norm"], "notes": "Tokenization via regexp_split_to_array + unnest." },
          { "name": "street_p4", "kind": "VIEW", "depends_on": ["street_word", "stop_word"], "notes": "Prefix-4 tokens with stop-word removal." },
          { "name": "p4_df", "kind": "VIEW", "depends_on": ["street_p4"], "notes": "DF across positions." },
          { "name": "p4_head_df", "kind": "VIEW", "depends_on": ["street_p4"], "notes": "Head DF (pos=1)." },
          { "name": "street_head_df", "kind": "VIEW", "depends_on": ["street_p4", "p4_head_df"], "notes": "Per-street head df." },
          { "name": "street_tail_min_df", "kind": "VIEW", "depends_on": ["street_p4", "p4_df"], "notes": "Per-street min tail df." }
        ]
      },

      "tracing_evidence": {
        "tracing_sessions": [
          {
            "tracing_id": "{TRACING_ID_0001}",
            "header_used": "X-TRACING_MDC_KEY",
            "breakpoints_json": "[{\"id\":\"bp_candidates\",\"class\":\"{JAVA_CLASS_CANDIDATE}\",\"line\":{LINE_CANDIDATE},\"watchExpr\":[\"{candidateCountVar}\",\"{topNVar}\",\"{pruneThresholdVar}\",\"{tokenNormalizedVar}\"]}]",
            "requests": [
              {
                "endpoint": "/admin/search-test/search-by-sql",
                "method": "GET",
                "body_excerpt": "EXISTS ( SELECT 1 FROM {THEORY_SCHEMA}.street_head_df h JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id=h.id WHERE h.id=a.street_id AND h.df_head>=400 AND t.min_tail_df<=5 )",
                "notes": "Trace H1 treatment group to validate candidate explosion + pruning behavior."
              }
            ],
            "logs_ref": "{TRACE_LOGS_HASH_OR_PATH}"
          }
        ],
        "key_runtime_variables": [
          "{candidateCountVar}",
          "{topNVar}",
          "{pruneThresholdVar}",
          "{tokenNormalizedVar}"
        ],
        "notes": "Round-1 tracing is illustrative; next iteration must quantify correlation between df_head and candidateCountVar and document pruning decisions."
      },

      "signatures": {
        "theory_signature": "{THEORY_SIG_SHA256_PLACEHOLDER}"
      }
    },

    "surrogate_index": {
      "level": "L2",
      "feature_views": [
        "{THEORY_SCHEMA}.street_word",
        "{THEORY_SCHEMA}.street_p4",
        "{THEORY_SCHEMA}.p4_df",
        "{THEORY_SCHEMA}.p4_head_df",
        "{THEORY_SCHEMA}.street_head_df",
        "{THEORY_SCHEMA}.street_tail_min_df"
      ],
      "invariants": [
        "df_head is a proxy for head-prefix collision and candidate explosion risk.",
        "min_tail_df captures existence of a very rare tail token that may be underweighted by runtime heuristics.",
        "Frequent head + rare tail is a distinctive region expected to produce a new error cluster (reason_family) and higher NotFoundRate."
      ]
    },

    "surrogate_validation": {
      "trace_alignment": {
        "planned_checks": [
          "corr(df_head, candidateCountVar) should be positive within and across city strata",
          "H1 group should show higher frequency of pruning events (topN truncation) than control",
          "H2 group should show candidate explosion but lower pruning-induced mismatch than H1"
        ],
        "status": "PENDING_NEXT_ITERATION"
      },
      "holdout_scoring": {
        "protocol": "holdout scoring-only; no active group search",
        "status": "PENDING_NEXT_ITERATION",
        "notes": "Round 1 provides initial empirical rates; next iteration must compute AUC/topk_lift on holdout bins with fixed protocol."
      }
    }
  }
}
~~~

---

## 2) What the evaluator actually receives (WHERE-suffix examples)

### H1 (Frequent head + rare tail)
```sql
EXISTS (
  SELECT 1
  FROM {THEORY_SCHEMA}.street_head_df h
  JOIN {THEORY_SCHEMA}.street_tail_min_df t ON t.id = h.id
  WHERE h.id = a.street_id
    AND h.df_head >= 400
    AND t.min_tail_df <= 5
)
