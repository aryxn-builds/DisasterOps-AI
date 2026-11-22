# Future research phases

These proposals are outside the committed foundation scope. Use synthetic fixtures and independent validation before considering integration. See [Roadmap](ROADMAP.md) for gates.

| Investigation and purpose | Dependencies and technical approach | Research challenge, safety and limitations | Evaluation |
| --- | --- | --- | --- |
| LoRa/Meshtastic fallback | Field hardware, authorized band/use, encrypted gateway, compact signed envelopes and store-and-forward IDs | Packet loss, duty limits and stale location. Keep drafts and receipts distinct, avoid cleartext PII. | Delivery, latency and battery drain across terrain and retries. |
| Sentinel-1 flood mapping | Licensed SAR scenes, reproducible preprocessing and georeferenced flood masks | Speckle, urban shadow and revisit delay. Mask cannot alone justify route closure. | IoU and omission/commission against timestamped labeled areas. |
| YOLOv8 + SAHI drone search | Approved aerial imagery, inference and georeference calibration, sliced detector | Tiny objects, occlusion and bystander privacy. Human review and permissions precede field collection. | Precision/recall by altitude and object size, geolocation error and compute cost. |
| Multimodal incident understanding | Redacted text/image sets, evidence references and typed extraction | Cross-modal contradictions and hallucinations; insufficient evidence remains uncertain. | Attribution, calibrated uncertainty and safety-critical miss rates. |
| Satellite and drone corroboration | Spatial-temporal fusion with provenance and independent observations | Time alignment, shared errors and no coverage. Avoid double counting derived sources. | Compare single- and multi-source evidence with held-out scenarios. |
| Simulation survival modeling | Synthetic or approved data, explicit assumptions and sensitivity analysis | Outcomes are simulated proxies; no clinical or survival prediction claims. | Stress-test decay assumptions and ranking stability. |
| SUMO traffic simulation | Versioned road graph, demand models, and scenario calibration | Evacuation behavior is uncertain. Simulation ETA is not a field promise. | Compare congestion scenarios, route validity and ETA variation. |
| Fairness-aware allocation | Zone definitions, audited eligibility, stable baseline and fairness constraints | Sparse data and conflicting fairness objectives. Never invent demographics. | Compare service gaps and delay tails with feasibility/cost trade-offs. |
| Multi-region coordination | Tenant roles, boundary adapters, policy and graph versioning | Cross-boundary data and resource rights; no integration without authorization. | Tenant isolation and simulated resource handovers. |
| Offline-first app | Device storage threat model, durable draft outbox and receipt reconciliation | Shared devices, stale location and non-delivery. Encrypt/minimize offline data and make drafts visible. | Airplane mode/reconnect, crash, duplicate and device loss tests. |
| Volunteer/NGO coordination | Scoped roles, eligibility verification and consent | Impersonation and unsafe tasking; no autonomous or unsupervised assignments. | Access tests and tabletop authorization drills. |
| Advanced geospatial analysis | PostGIS, CRS and graph metadata, validated exposure layers | Data resolution, licensing and reidentification risks. | Spatial accuracy, query performance and sensitivity by resolution. |
| Observability and scaling | Redacted metrics, worker replay, documented load and audited traces | Operational complexity and sensitive telemetry. | Load, backpressure, recovery and duplicate-effect tests. |

The [original notes](../MODULES.md) preserve candidate methods and datasets. Confirm suitability, licensing, ethics and measurement protocols before making them project dependencies.
