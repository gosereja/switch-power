# Data model
Catalogue: raw model/list entries, timestamp, actual spawn models/efforts.
Snapshot expires in 24h. IDs remain verbatim.
Session: random task ID, description, current user turn, boundary-resolution flag,
scopes, exact grants, pending proposal, excluded failed tuples.
Grant: exact model, effort, task, scope, live-user evidence hash and source turn.
New task empties grants/proposals/failures. No wildcard grants.
Helper ties evidence to hook-captured user text. Semantic text classification and
task boundaries still belong to the coordinator; this is not identity attestation.
