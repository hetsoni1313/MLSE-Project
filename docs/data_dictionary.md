# Data Dictionary

## Database Tables

### `request_logs`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| timestamp | DateTime | Request timestamp (UTC) |
| request_id | String(64) | Unique request identifier |
| user_id | String(128) | User identifier (for sticky routing) |
| route | String(32) | Route used: "baseline" or "local" |
| model_name | String(128) | Model identifier |
| input_text | Text | Customer message |
| predicted_label | String(128) | Model's predicted intent label |
| ground_truth_label | String(128) | True label (when available) |
| correct | Boolean | Whether prediction matches ground truth |
| valid_output | Boolean | Whether prediction is a valid Banking77 label |
| input_tokens | Integer | Input token count |
| output_tokens | Integer | Output token count |
| latency_ms | Float | End-to-end latency in milliseconds |
| tokens_per_second | Float | Output tokens per second |
| estimated_cost | Float | Estimated cost in USD |
| fallback_used | Boolean | Whether fallback to baseline occurred |
| fallback_reason | String(256) | Reason for fallback |
| error | Text | Error message if any |
| experiment_mode | String(32) | Routing mode during this request |
| experiment_id | String(64) | Experiment run identifier |

### `rollback_events`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| event_id | String(64) | Unique rollback event ID |
| timestamp | DateTime | When rollback was triggered |
| trigger_type | String(32) | "accuracy", "error_rate", or "p95_latency" |
| metric_value | Float | Actual metric value that triggered rollback |
| threshold_value | Float | Configured threshold that was violated |
| previous_baseline_pct | Integer | Baseline % before rollback |
| previous_local_pct | Integer | Local % before rollback |
| new_baseline_pct | Integer | Baseline % after rollback (100) |
| new_local_pct | Integer | Local % after rollback (0) |
| evaluation_window | Integer | Number of recent requests evaluated |
| details | Text | Human-readable description |

### `experiment_runs`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| experiment_id | String(64) | Unique experiment identifier |
| name | String(256) | Experiment name |
| description | Text | Description |
| routing_mode | String(32) | Routing mode used |
| baseline_pct | Integer | Baseline traffic percentage |
| local_pct | Integer | Local traffic percentage |
| model_name | String(128) | Model used |
| started_at | DateTime | Start time |
| ended_at | DateTime | End time |
| total_requests | Integer | Total requests in experiment |
| config_snapshot | Text | JSON snapshot of configuration |

### `evaluation_summaries`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| timestamp | DateTime | Evaluation timestamp |
| model_name | String(128) | Model evaluated |
| dataset_hash | String(64) | SHA-256 of evaluation dataset |
| accuracy | Float | Classification accuracy |
| macro_f1 | Float | Macro-averaged F1 score |
| invalid_rate | Float | Rate of invalid predictions |
| mean_latency_ms | Float | Mean latency |
| p50_latency_ms | Float | 50th percentile latency |
| p95_latency_ms | Float | 95th percentile latency |
| cost_per_query | Float | Average cost per query |
| total_requests | Integer | Number of requests evaluated |
| git_commit | String(40) | Git commit SHA |

### `routing_config_history`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| timestamp | DateTime | Change timestamp |
| mode | String(32) | New routing mode |
| baseline_pct | Integer | New baseline percentage |
| local_pct | Integer | New local percentage |
| changed_by | String(128) | Who made the change |
| reason | Text | Reason for change |

