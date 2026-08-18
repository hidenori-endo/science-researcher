from __future__ import annotations

from .db import GraphStore
from .embeddings import HashEmbedder
from .embedding_openai import OpenAIEmbeddingProvider
from .postgres_store import PostgresGraphStore
from .pipeline import DiscoveryEngine
from .provider import HeuristicProvider, ReasoningProvider
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
    retriever = MultiAxisRetriever(store, embedder or HashEmbedder())
    return DiscoveryEngine(
        store=store,
        retriever=retriever,
        generator=generator or HeuristicProvider(),
        critic=critic or HeuristicProvider(),
    )
