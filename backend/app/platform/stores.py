from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.models import IndexedDocument, Repository
from app.rag.retriever import SearchResult, search_repository_history


class RelationalStore(Protocol):
    def repository_exists(self, repository_id: int) -> bool:
        ...


class VectorStore(Protocol):
    def search(self, repository_id: int, query: str, top_k: int = 5) -> list[SearchResult]:
        ...


class GraphStore(Protocol):
    def add_node(self, node_id: str, labels: list[str], properties: dict[str, object]) -> None:
        ...

    def add_edge(self, source_id: str, target_id: str, edge_type: str, properties: dict[str, object] | None = None) -> None:
        ...

    def neighbors(self, node_id: str, edge_type: str | None = None) -> list[dict[str, object]]:
        ...


@dataclass
class SQLAlchemyRelationalStore:
    db: Session

    def repository_exists(self, repository_id: int) -> bool:
        return self.db.get(Repository, repository_id) is not None


@dataclass
class LocalVectorStore:
    db: Session

    def search(self, repository_id: int, query: str, top_k: int = 5) -> list[SearchResult]:
        return search_repository_history(self.db, repository_id, query, top_k)

    def indexed_count(self, repository_id: int) -> int:
        return self.db.query(IndexedDocument).filter_by(repository_id=repository_id).count()


class LocalGraphStore:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, object]] = {}
        self.edges: list[dict[str, object]] = []

    def add_node(self, node_id: str, labels: list[str], properties: dict[str, object]) -> None:
        self.nodes[node_id] = {"id": node_id, "labels": labels, "properties": properties}

    def add_edge(self, source_id: str, target_id: str, edge_type: str, properties: dict[str, object] | None = None) -> None:
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Graph edges require existing source and target nodes")
        self.edges.append({"source": source_id, "target": target_id, "type": edge_type, "properties": properties or {}})

    def neighbors(self, node_id: str, edge_type: str | None = None) -> list[dict[str, object]]:
        matches = []
        for edge in self.edges:
            if edge["source"] != node_id:
                continue
            if edge_type and edge["type"] != edge_type:
                continue
            target = self.nodes.get(str(edge["target"]))
            if target:
                matches.append({"edge": edge, "node": target})
        return matches
