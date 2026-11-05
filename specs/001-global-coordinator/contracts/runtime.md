# Runtime contract
Only native spawn executes agents. CLI check never spawns or confirms backend.
Exit 0 means locally permitted; nonzero denies.
Catalogue reads all model/list pages and intersects actual spawn allowlist.
`task --new` resets grants; `task --continue` resolves same-task steering.
`scope` registers bounded work. `grant` requires exact tuple/scope, captured live
turn and verbatim quote. `propose` names exact tuple/scope/reason for user consent.
`check` requires session, task-prefixed name, explicit model and effort.
Native hooks emit documented JSON deny, never unsupported ask/continue fields.
