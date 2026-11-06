# Historical service regressions

These tests assert the retired account/API/broker/database contracts. They are preserved as history, not passing evidence for the new runtime. Two service-specific unit files were moved here; original mixed native/visual/packaging tests were copied before removing only their retired API cases from active files. Current engine cases remain in the active suite.

The old tests/integration service-only modules are also excluded from the default testpaths; they remain in place for historical recovery. They require the old optional service dependencies and PYTHONPATH=services/api. They are not required by the simplified application. Replacement filesystem/process/route boundaries are covered by tests/runtime and apps/web/tests/runtime.test.mjs plus real UI tests. No legacy conversion result has been promoted or fabricated.
