from __future__ import annotations

from .db import GraphStore
from .embeddings import HashEmbedder
from .hybrid_retrieval import HybridRetriever
from .pipeline import DiscoveryEngine
from .postgres_store import PostgresGraphStore
from .provider import HeuristicProvider, ReasoningProvider
from .research import ResearchIndex
from .retrieval import MultiAxisRetriever
from .seed import SEED_NODES


def initialize_store(path: str) -> GraphStore:
    store = GraphStore(path)
    store.initialize()
    return store


def initialize_postgres_store(database_url: str) -> PostgresGraphStore:
    store = PostgresGraphStore(database_url)
    store.initialize()
    return store


def seed_store(store: object, embedder: object | None = None) -> None:
    retriever = MultiAxisRetriever(store, embedder or HashEmbedder())
    for node in SEED_NODES:
        retriever.index_node(node)


def build_engine(
    store: object,
    *,
    generator: ReasoningProvider | None = None,
    critic: ReasoningProvider | None = None,
    embedder: object | None = None,
) -> DiscoveryEngine:
    resolved_embedder = embedder or HashEmbedder()
    node_retriever = MultiAxisRetriever(store, resolved_embedder)
    retriever = HybridRetriever(
        store,
        node_retriever=node_retriever,
        research_index=ResearchIndex(store, resolved_embedder),
    )
    return DiscoveryEngine(
        store=store,
        retriever=retriever,
        generator=generator or HeuristicProvider(),
        critic=critic or HeuristicProvider(),
    )
