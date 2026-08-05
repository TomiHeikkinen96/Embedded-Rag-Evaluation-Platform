# Local LLM and RAG Evaluation Harness for Embedded Engineering

Local-first portfolio project for evaluating whether retrieval-augmented generation (RAG) makes local language models more accurate, grounded, and useful for embedded software engineering.

The project is growing from a document retrieval demo into an inspectable AI evaluation harness: a system that runs controlled model experiments, records the complete execution configuration, and separates retrieval failures from model and context-use failures.

The current corpus is ESP32 documentation. The planned benchmark will compare local models under three conditions: no retrieved context, context produced by the RAG pipeline, and known-good oracle context. This makes it possible to measure when RAG helps smaller models instead of merely demonstrating that a chatbot can search documents.

> **Project status:** the local ingestion and retrieval foundation is implemented. Model execution, answer evaluation, and experiment tracking are the next major workstream. See [NEXT_STEPS.md](NEXT_STEPS.md) for the planned harness design.

## Why This Exists

This repo is a lightweight experimentation platform for evaluating local LLMs and context-building methods in embedded development workflows.

Questions this repo is trying to answer:
- How should embedded reference material be ingested so it stays repeatable and inspectable?
- How can ingestion reprocess only changed data instead of rebuilding everything?
- How do chunking strategy, embedding model choice, and storage format affect retrieval quality?
- Does retrieved hardware documentation improve answer correctness and reduce hallucinations?
- Can a small local model with RAG outperform a larger model without domain context?
- Did an unsuccessful answer fail because of retrieval, model capability, or poor context use?
- How reproducibly can model, prompt, retrieval, latency, and scoring changes be compared?

## Planned Harness

The intended harness will keep the experimental layers explicit:

- a versioned engineering question set with reference facts and relevant source locations
- interchangeable local model adapters, beginning with an OpenAI-compatible Ollama endpoint
- controlled no-context, retrieved-context, and oracle-context runs
- retrieval metrics such as Recall@k and MRR
- answer-level correctness, grounding, citation, refusal, and latency measurements
- durable experiment records containing prompts, settings, retrieved chunks, outputs, and scores
- optional LangChain/LangGraph and LlamaIndex adapters for framework comparison
- containerized local workflows once the basic runner is stable

LangChain, LangGraph, LlamaIndex, and eventually durable workflow orchestration are treated as technologies to evaluate or integrate where useful. The core benchmark remains framework-independent so that a framework change does not silently change the experiment itself.

## Current Demo

Right now this repo provides:
- local PDF ingestion from `data/`
- file-level change detection using hashes
- deleted-file detection for removed source PDFs
- chunk generation for PDFs
- sentence-transformer embeddings
- SQLite metadata storage
- explicit index-build metadata and vector-to-chunk mapping in SQLite
- FAISS vector indexing with durable vector ids
- simple local search over indexed content

The current implementation is intentionally local-first. Source data is processed locally for this demo and is not intended to be redistributed through the repository.

Current indexing tradeoff:
- normal ingest runs update FAISS incrementally by removing and adding only the affected document vectors
- `--force-rebuild` still clears storage and rebuilds the full active index from scratch
- this is intentional for the current stage of the project

Why keep it this way for now:
- simple implementation
- minimal moving parts
- easier to reason about during experimentation
- faster to iterate on ingestion logic and storage design

What is explicit now:
- each index build is recorded in SQLite
- each FAISS `vector_id` is mapped to a durable `chunk_id`
- search resolves FAISS hits through stored index metadata instead of relying on repeated row ordering
- when a tracked PDF is removed from `data/`, its chunks and vectors are deleted from the active index state

Current limitation:
- vector ids are durable within the active index state, but `--force-rebuild` intentionally assigns a fresh index from scratch
- larger corpora may still justify additional work such as embedding reuse across experimental rebuilds, richer index-version history, or more sophisticated update policies

## Install

Tested with:

```bash
python3 --version
Python 3.12.3
```

If you use an older Python such as `3.10.x`, setup or runtime behavior may fail. For now, prefer Python `3.12`.

```bash
source ./setup_venv.sh
```

Note: This script targets Linux/macOS shells. On Windows, use WSL or create the virtual environment manually:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The script creates `.venv` if needed, activates it with the standard Ubuntu shell command `source .venv/bin/activate`, upgrades `pip`, and installs from `requirements.txt`. If you run `./setup_venv.sh` instead of `source ./setup_venv.sh`, setup still runs, but the virtual environment will not stay active in your current terminal after the script exits.

If you have CUDA-enabled PyTorch already installed, the embedder will use GPU automatically.

## Run

Place PDFs anywhere under `./data/`, then run:

```bash
python ingest.py
```

To rebuild from scratch:

```bash
python ingest.py --force-rebuild
```

After ingesting documents:

```bash
python search_index.py
```

## Project Layout

```text
.
├── ingest.py
├── search_index.py
├── data/
├── storage/
├── chunkers/
├── processing/
└── utils/
```

## Roadmap

- Define a structured, versioned embedded-engineering benchmark dataset
- Add a reusable retriever interface around the current FAISS and SQLite implementation
- Add local model execution through a narrow provider adapter
- Compare no-context, retrieved-context, and oracle-context answers
- Persist complete experiment configurations and results for reproducible comparisons
- Add deterministic retrieval and answer scoring before introducing LLM-as-judge metrics
- Compare selected LangChain/LangGraph and LlamaIndex integrations without hiding the custom retrieval pipeline
- Containerize the repeatable local workflow and consider distributed orchestration only when experiments require it
