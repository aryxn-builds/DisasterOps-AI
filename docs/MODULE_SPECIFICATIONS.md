# Module specifications

Use this document for module boundaries and acceptance. [API contracts](API_CONTRACTS.md) describes implemented endpoints. [Original module notes](../MODULES.md) preserve research alternatives and example designs.

## 1. Find People

**Partially implemented.** Collect a traceable distress report even with no GPS. Inputs include authenticated button or confirmed shake actions, optional coordinate pair, accuracy, battery and message, and signed Android SMS. Outputs are durable reports and separate safety check-ins. Browser geolocation/motion, the SMS parser, and SQL transactions support the flow. See [citizen router](../disasterops/routers/citizen.py), [SMS parser](../disasterops/services/sms.py), and [browser workflows](../app.js).

`CitizenSafety` stores SAFE or NEEDS_HELP; absence implies Unknown. The browser sends SAFE via check-in and HELP via SOS. No automatic expiry or override exists. The API accepts coordinates but the current UI has no manual location entry. The authenticated UI can request GPS; a consent link can collect a separate fix. Incoming SMS text stays unverified and may lack usable coordinates. Idempotency applies to the sender-scoped browser key or gateway event key, not semantic duplicates.

**Target:** source provenance with device/report timestamps, manual location with accuracy/unknown annotations, policy-defined check-in expiry, opt-in family linking, and low-battery telemetry. LoRa, drone detections and satellite observations are later adapters. Enforce separate authority for proxy submissions and never infer identity from SMS text. Gate: offline drafts and denied GPS visibly preserve uncertainty, duplicate callbacks create one record, and stale or absent check-ins never imply danger.

## 2. Hospital Enquiry

**Simulated.** [app.js](../app.js) renders static hospital capacity and distance examples from `HOSPITALS`. No hospital account, write route, inventory database, measured distance or clinical integration exists.

**Target:** authorize hospital registration and facility-scoped updates. Model hospital, specialty, beds/ICU, ambulance availability, blood and medicines using typed quantities with units, provenance and freshness. Expose scoped inventory reads/writes and transactional reservation and confirmation. Ground any natural-language enquiry in an approved read tool. Filter recommendations by specialty, freshness, and reachable travel time. Stale or unavailable capacity becomes explicit unknown, and reservation conflicts are visible. Gate: stale or medically unsuitable rows never become confirmed destinations; concurrent reservations cannot exceed verified availability. Add expiry, reconciliation and audit before integrating clinical data.

## 3. Dynamic Map

**Partially implemented.** `renderMap` in [app.js](../app.js) plots known coordinates for the authorized page using Leaflet and external base tiles. The role-scoped report API supplies points. Location-free reports remain visible in the queue. There is no graph, hazard layer, routing computation or matrix.

**Target:** build versioned directed road graphs using OSMnx and NetworkX, with edge length, travel seconds, mode and closure effects. Normalize flood polygons and road closures to a common CRS, intersect against relevant edges, and publish changes only after validation and review. Routing returns A* or Dijkstra paths, cost, alternatives and OD travel-time matrix with graph version. Handle disconnected components and uncertainty explicitly. Keep precise personal data out of tile URLs and public layers. Gate: all routes obey direction and closures, unreachable destinations return a typed result, and material changes are traceable triggers for replanning.

## 4. Rescue Prioritization

**Partially implemented.** [Rescue router](../disasterops/routers/rescue.py) links one report to one incident and one responder assignment, then records responder confirmation. There is no team registry, vehicle inventory, hospital matching, optimizer or external dispatch.

**Target:** freeze snapshots of incident needs, capabilities, shifts, vehicle capacity, hazards and hospital intake. OR-Tools may evaluate a constrained routing or assignment model and return candidate routes, ETA, unmet demand and infeasibility reasons. Record solver parameters, input versions and approval. Separate prioritization from hard constraints. If time/feasibility fails, offer a safe manual review path. Replanning proposes changes and preserves already acknowledged actions until an authorized decision. Gate: deterministic fixture validation enforces capacity and availability, and only an approved current candidate can create a simulated mission. Compare with [evaluation baselines](../TESTING_STRATEGY.md).

## 5. Report Verification

**Planned.** Current authentication, range validation, transport replay controls and operator review provide a foundation. There is no evidence store, classifier or automated corroboration.

**Target:** accept an immutable report with source/time/uncertainty and authorized associated evidence. Compute exact and near-duplicate candidates, spatiotemporal clusters, plausibility and source-reliability indicators; preserve originals. Consider text classification, metadata and image similarity, and independent corroboration as advisory evidence. Output versioned assessments with references, contradictions and uncertainty for manual verification. Allow safe note/review interfaces and record actor/reason. Do not merge people counts based solely on duplicate messages or image similarity. Gate: low confidence, malformed model output or tool outage never erases a critical SOS. Evaluate false negatives, false positives, calibration and reviewer outcomes across channels and connectivity conditions.

Dependencies, phase gates and model interfaces are described in [Roadmap](ROADMAP.md), [Data model](DATA_MODEL.md), and [AI design](AI_AGENT_DESIGN.md).
