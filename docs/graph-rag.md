# Graph-RAG

RHD now has a local graph abstraction that can represent verified repository relationships.

Implemented graph foundations:

- `GraphStore` protocol
- local in-process graph backend
- verified-node requirement for edges
- Repository, File, and Symbol nodes from code intelligence
- `CONTAINS` and `DEFINES` edges

Planned graph expansion:

- Issue
- PR
- Commit
- Release
- Contributor
- Test
- SecuritySignal
- DuplicateCluster

Potential evidence path:

Issue #8 -> related PR -> changed file -> symbol -> release v1.2.0

Graph-RAG must only show verified paths. If a path cannot be constructed from synchronized repository data, RHD must report insufficient evidence.
