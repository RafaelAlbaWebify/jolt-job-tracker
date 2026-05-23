# LinkedIn Job GUI MVP v23

Classifier cleanup build. Keeps v20 capture/logging behavior and adds Rafael's current hard filters:

- Mandatory non-Spanish/English language requirements are hard-discarded.
- Hybrid/onsite roles more than ~30 km from Vigo are hard-discarded.
- Remote roles are not discarded by distance.
- Night shift/weekend/on-call risks are kept as manual review instead of hidden.
- Remote weak/stretch but realistic IT support/application support roles are kept as C/manual review more often.

Install by expanding the zip into the project root and copying the package contents over the existing files.
