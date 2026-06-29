# 📊 FinVista Capital – Enterprise Financial Intelligence Assistant

RAG-powered AI assistant built with **Python 3.11**, **Groq (llama-3.3-70b-versatile)**, **Google Gemini Embeddings**, **ChromaDB**, **Streamlit**, **Docker**, and **Kubernetes (EKS)**.

---

## Stack at a Glance

| Component | Technology |
|---|---|
| LLM | Groq `llama-3.3-70b-versatile` |
| Embeddings | Google Gemini `gemini-embedding-001` |
| Vector DB | ChromaDB 0.4.24 (persistent, cosine similarity) |
| PDF Parsing | PyMuPDF (fitz) |
| Text Splitting | LangChain `RecursiveCharacterTextSplitter` |
| UI | Streamlit 1.35.0 |
| Container | Docker (multi-stage, python:3.11-slim) |
| Orchestration | Kubernetes (AWS EKS, eu-north-1) |
| CI/CD | GitHub Actions (3-job pipeline) |

> **Free tier friendly:** Groq provides 1,000 free LLM requests/day (no credit card). Gemini embeddings are free under Google AI Studio. ChromaDB runs locally with no infrastructure cost.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP (port 80)
┌────────────────────────────▼────────────────────────────────────────┐
│              Kubernetes (EKS) – namespace: finvista                 │
│                                                                     │
│  ┌──────────────────────────────────────────────┐                  │
│  │  Streamlit App (Deployment, 2–10 replicas)   │                  │
│  │                                              │                  │
│  │  ┌────────────┐   ┌────────────────────────┐ │                  │
│  │  │  RAG       │   │  ChromaDB (PVC 10Gi)   │ │                  │
│  │  │  Engine    │◄──│  Vector Database       │ │                  │
│  │  └─────┬──────┘   └────────────────────────┘ │                  │
│  │        │                                      │                  │
│  └────────┼─────────────────────────────────────┘                  │
│           │                                                         │
└───────────┼─────────────────────────────────────────────────────────┘
            │ API calls
┌───────────▼──────────────────────────┐  ┌──────────────────────────┐
│        Google Gemini API             │  │        Groq API           │
│  • gemini-embedding-001 (Embeddings) │  │  • llama-3.3-70b-versatile│
└──────────────────────────────────────┘  └──────────────────────────┘
```

---

## RAG Pipeline

```
PDF Upload ──► PDF Parser (PyMuPDF) ──► Text Splitter (LangChain)
                                               │  chunk_size=1000
                                               │  chunk_overlap=200
                                               ▼
                              Gemini Embedding API (RETRIEVAL_DOCUMENT)
                              gemini-embedding-001 → 3,072-dim vectors
                                               │
                                               ▼
                                    ChromaDB (upsert, cosine space)
                                    MD5(source+page+chunk) as doc ID

User Query ──────────────────► Query Embedding (RETRIEVAL_QUERY)
                                               │
                                               ▼
                                  Cosine Similarity Search (top-5)
                                               │
                                               ▼
                            Context Chunks + Last 6 Conversation Turns
                                               │
                                               ▼
                                    Prompt Construction
                                    (system + history + context + query)
                                               │
                                               ▼
                           Groq LLM (llama-3.3-70b-versatile)
                           max_tokens=1024, temperature=0.1
                                               │
                                               ▼
                               Answer + Source Citations ──► User
```

---

## Project Structure

```
finvista-assistant/
├── app/
│   ├── rag_engine.py          # Core RAG logic (parse, chunk, embed, retrieve, generate)
│   ├── streamlit_app.py       # Streamlit web UI (chat, history, help tabs)
│   ├── preload.py             # Auto-indexes 5 bundled PDFs on pod startup
│   ├── startup.sh             # Container entrypoint: preload → streamlit
│   ├── .streamlit/
│   │   └── config.toml        # maxUploadSize=200, maxMessageSize=200
│   └── data/
│       ├── 01_FinVista_Annual_Report_2024.pdf
│       ├── 02_FinVista_Investment_Policy_2024.pdf
│       ├── 03_FinVista_Compliance_Manual_2024.pdf
│       ├── 04_FinVista_Market_Intelligence_Q4_2024.pdf
│       └── 05_FinVista_Risk_Assessment_Framework.pdf
├── k8s/
│   ├── 01-namespace-configmap.yaml   # Namespace: finvista + ConfigMap
│   ├── 02-secret.yaml                # GEMINI_API_KEY + GROQ_API_KEY
│   ├── 03-pvc.yaml                   # 10Gi gp3 PVC for ChromaDB
│   ├── 04-deployment.yaml            # 2 replicas, non-root, HPA-ready
│   ├── 05-service-ingress.yaml       # LoadBalancer port 80 → 8501
│   └── 06-hpa.yaml                   # Scale 2–10 pods on CPU≥70% / Mem≥80%
├── tests/
│   └── test_rag_engine.py     # 12 unit tests, all services mocked
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # test → ECR push → EKS deploy (~3 min)
├── Dockerfile                 # Multi-stage, python:3.11-slim, non-root UID 1000
├── requirements.txt           # Pinned deps (incl. opentelemetry for chromadb)
├── .env.example               # Copy to .env and fill in your keys
└── README.md
```

---

## Phase 1 – Local Development

### Prerequisites

- Python **3.11** exactly — ChromaDB 0.4.24 is **not** compatible with 3.12+
- [Gemini API key](https://aistudio.google.com) — free tier (Google AI Studio)
- [Groq API key](https://console.groq.com/keys) — free tier, no credit card required

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Sasank2126/finvista-assistant.git
cd finvista-assistant

# 2. Create virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies (~90 sec with pinned versions)
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env and set:
#   GEMINI_API_KEY=AIzaSy-your-key-here
#   GROQ_API_KEY=gsk_your-key-here

# 5. Index the 5 bundled PDFs
python3 app/preload.py

# 6. Launch the app
streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=8501
# Opens at http://localhost:8501
```

---

## Phase 2 – Docker

```bash
# Build image
docker build -t finvista-assistant:latest .

# Run (keys passed as env vars; ChromaDB mounted as a volume)
docker run -p 8501:8501 \
  -e GEMINI_API_KEY=your_gemini_key \
  -e GROQ_API_KEY=your_groq_key \
  -v $(pwd)/chroma_db:/app/chroma_db \
  finvista-assistant:latest

# Open http://localhost:8501
```

> **Note:** The container runs as non-root user `finvista` (UID 1000). The `startup.sh` entrypoint runs `preload.py` first, then launches Streamlit with `exec` so the bundled PDFs are auto-indexed on every fresh start.

---

## Phase 3 – Kubernetes (EKS) Deployment

### Prerequisites

- AWS CLI configured (`aws configure`)
- `kubectl` and `eksctl` installed
- EKS cluster running in `eu-north-1`
- ECR repository created

### Step-by-step

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name finvista-assistant --region eu-north-1

# 2. Authenticate Docker to ECR
ECR_URI=$(aws ecr describe-repositories \
  --repository-names finvista-assistant \
  --region eu-north-1 \
  --query 'repositories[0].repositoryUri' --output text)

aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# 3. Build and push
docker build -t $ECR_URI:latest .
docker push $ECR_URI:latest

# 4. Update image URI in k8s/04-deployment.yaml
sed -i "s|YOUR_ECR_REGISTRY/finvista-assistant:latest|$ECR_URI:latest|g" \
  k8s/04-deployment.yaml

# 5. Apply all manifests
kubectl apply -f k8s/

# 6. Monitor rollout
kubectl rollout status deployment/finvista-assistant -n finvista

# 7. Get the LoadBalancer URL
kubectl get service finvista-service -n finvista
# Access the app at: http://<EXTERNAL-IP>
```

### Kubernetes Resources

| Manifest | Kind | Key Config |
|---|---|---|
| `01-namespace-configmap.yaml` | Namespace + ConfigMap | Namespace: `finvista`; env vars injected into pods |
| `02-secret.yaml` | Secret | `GEMINI_API_KEY` + `GROQ_API_KEY` (base64) |
| `03-pvc.yaml` | PersistentVolumeClaim | 10Gi, `gp3`, `ReadWriteOnce` — ChromaDB persistence |
| `04-deployment.yaml` | Deployment | 2 replicas, `runAsNonRoot=true`, UID 1000, rolling update (`maxUnavailable=0`) |
| `05-service-ingress.yaml` | Service (LoadBalancer) | Port 80 → 8501; idle-timeout=600s for large PDF uploads |
| `06-hpa.yaml` | HorizontalPodAutoscaler | 2–10 replicas; scale on CPU≥70% OR Memory≥80% |

---

## Phase 4 – CI/CD (GitHub Actions)

The pipeline triggers on every push to `main`/`develop` and every PR to `main`. Three sequential jobs run in ~3 minutes total.

```
Push to main
    │
    ▼
Job 1: test (~40s)
  └─ pytest tests/ -v --cov=app
    │
    ▼
Job 2: build-and-push (~107s)  [main branch only]
  └─ docker build → push :sha + :latest to ECR
    │
    ▼
Job 3: deploy (~31s)
  └─ kubectl apply k8s/ manifests
  └─ sed inject commit SHA into deployment.yaml → kubectl apply
  └─ kubectl rollout status --timeout=300s
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key (`AIzaSy...`) |
| `GROQ_API_KEY` | Groq console key (`gsk_...`) |
| `AWS_ACCESS_KEY_ID` | IAM user access key (`AKIA...`) with ECR push + EKS deploy permissions |
| `AWS_SECRET_ACCESS_KEY` | Corresponding IAM secret key |

---

## Running Tests

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=app

# Expected: 12 passed in < 5 seconds
# No live API calls — all services (Gemini, Groq, ChromaDB) are mocked
```

### Test Coverage

| Test | What It Verifies |
|---|---|
| `test_chunk_pages_returns_list` | Output is a list with ≥ input page count |
| `test_chunk_pages_required_keys` | Every chunk has `text`, `source`, `page`, `chunk` keys |
| `test_chunk_pages_source_preserved` | `source` field matches input filename |
| `test_build_prompt_contains_query` | User query appears in constructed prompt |
| `test_build_prompt_contains_source` | Source filename appears in prompt context |
| `test_build_prompt_contains_history` | Prior conversation turns included in prompt |
| `test_collection_stats_shape` | Returns dict with `total_chunks`, `document_count`, `documents` |
| `test_parse_pdf_returns_pages` | `parse_pdf()` returns a list of page dicts |
| `test_semantic_search_returns_hits` | Returns hits with correct `source` and `similarity` |
| `test_semantic_search_empty_collection_returns_empty` | Returns `[]` when ChromaDB is empty |
| `test_delete_returns_true_when_found` | `delete_document()` returns `True` when chunks exist |
| `test_delete_returns_false_when_not_found` | Returns `False` for nonexistent document |

---

## Infrastructure Details

| Resource | Value |
|---|---|
| AWS Region | `eu-north-1` (Stockholm) — EU data residency |
| EKS Cluster | `finvista-cluster` — 2 × t3.medium nodes |
| ECR Repository | `106062677957.dkr.ecr.eu-north-1.amazonaws.com/finvista-assistant` |
| Estimated Cost | ~$5.50/day — **delete cluster when not in use** |

---

## Troubleshooting

**`GEMINI_API_KEY` not set**
→ Add it to `.env` for local, or verify `finvista-secrets` in Kubernetes: `kubectl get secret finvista-secrets -n finvista`

**`GROQ_API_KEY` not set**
→ Get a free key at [console.groq.com/keys](https://console.groq.com/keys) — no credit card needed

**ChromaDB permission error on K8s**
→ Verify PVC is bound: `kubectl get pvc -n finvista`

**Pod CrashLoopBackOff**
→ Check logs: `kubectl logs -l app=finvista-assistant -n finvista`

**Knowledge base empty after fresh deploy**
→ `preload.py` auto-indexes on startup if `GEMINI_API_KEY` is set and ChromaDB is empty. Check pod logs for preload output.

**Python version error**
→ Use Python 3.11 exactly. ChromaDB 0.4.24 is incompatible with 3.12+.

**Slow embeddings**
→ Gemini free tier has rate limits. The code batches 100 chunks per API call to minimise requests.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | — | Google AI Studio key for embeddings |
| `GROQ_API_KEY` | ✅ Yes | — | Groq key for LLM inference |
| `CHROMA_DB_PATH` | No | `./chroma_db` | Path for ChromaDB persistence |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

---

*Built with Groq · Gemini · ChromaDB · Streamlit · Docker · Kubernetes*
*GitHub: [Sasank2126/finvista-assistant](https://github.com/Sasank2126/finvista-assistant) | AWS EKS: finvista-cluster, eu-north-1*