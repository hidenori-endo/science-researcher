from __future__ import annotations

from .db import GraphStore
from .embeddings import HashEmbedder
from .pipeline import DiscoveryEngine
from .provider import HeuristicProvider, ReasoningProvider
from .retrieval import MultiAxisRetriever
from .seed import SEED_NODES


def initialize_store(path: str) -> GraphStore:
    store = GraphStore(path)
    store.initialize()
    return store


def seed_store(store: GraphStore) -> None:
    retriever = MultiAxisRetriever(store, HashEmbedder())
    for node in SEED_NODES:
        retriever.index_node(node)


def build_engine(
    store: GraphStore,
    *,
    generator: ReasoningProvider | None = None,
    critic: ReasoningProvider | None = None,
) -> DiscoveryEngine:
    retriever = MultiAxisRetriever(store, HashEmbedder())
    return DiscoveryEngine(
        store=store,
        retriever=retriever,
        generator=generator or HeuristicProvider(),
        critic=critic or HeuristicProvider(),
    )
