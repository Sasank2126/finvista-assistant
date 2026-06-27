# 📊 FinVista Capital – Enterprise Financial Intelligence Assistant

RAG-powered AI assistant built with **Python**, **Google Gemini**, **ChromaDB**, **Streamlit**, **Docker**, and **Kubernetes (EKS)**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS
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
┌───────────▼───────────────────────────────────────────────────────┐
│           Google Gemini API                                        │
│   • gemini-1.5-flash (LLM)                                        │
│   • models/embedding-001 (Embeddings)                             │
└───────────────────────────────────────────────────────────────────┘
```

## RAG Pipeline

```
PDF Upload ──► PDF Parser (PyMuPDF) ──► Text Splitter (LangChain)
                                               │
                                               ▼
                                    Gemini Embedding API
                                               │
                                               ▼
                                      ChromaDB (persist)
                                               │
User Query ──────────────────► Query Embedding (Gemini)
                                               │
                                               ▼
                                    Semantic Search (cosine)
                                               │
                                               ▼
                             Context Chunks + Conversation History
                                               │
                                               ▼
                                    Prompt Construction
                                               │
                                               ▼
                                  Gemini LLM (gemini-1.5-flash)
                                               │
                                               ▼
                               Answer + Source Citations ──► User
```

---

## Project Structure

```
finvista/
├── app/
│   ├── rag_engine.py        # Core RAG logic (parse, embed, retrieve, generate)
│   └── streamlit_app.py     # Streamlit web UI
├── k8s/
│   ├── 01-namespace-configmap.yaml
│   ├── 02-secret.yaml
│   ├── 03-pvc.yaml
│   ├── 04-deployment.yaml
│   ├── 05-service-ingress.yaml
│   └── 06-hpa.yaml
├── tests/
│   └── test_rag_engine.py
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Phase 1 – Local Development

### Prerequisites
- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com) (free tier works)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/finvista-assistant.git
cd finvista-assistant

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_actual_key

# 5. Run the application
streamlit run app/streamlit_app.py
# Opens at http://localhost:8501
```

---

## Phase 2 – Docker

```bash
# Build
docker build -t finvista-assistant:latest .

# Run
docker run -p 8501:8501 \
  -e GEMINI_API_KEY=your_key_here \
  -v $(pwd)/chroma_db:/app/chroma_db \
  finvista-assistant:latest

# Open http://localhost:8501
```

---

## Phase 3 – Kubernetes (EKS) Deployment

### Prerequisites
- AWS CLI configured
- `kubectl` installed
- EKS cluster running
- ECR repository created

### Step-by-step

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name finvista-assistant --region us-east-1

# 2. Build and push image
ECR_URI=$(aws ecr describe-repositories \
  --repository-names finvista-assistant \
  --query 'repositories[0].repositoryUri' --output text)

aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI

docker build -t $ECR_URI:latest .
docker push $ECR_URI:latest

# 3. Update k8s/04-deployment.yaml with your ECR URI

# 4. Create Gemini API key secret
kubectl create secret generic finvista-secrets \
  --from-literal=GEMINI_API_KEY=your_key_here \
  --namespace finvista   # (namespace auto-created in step 5)

# 5. Apply all manifests
kubectl apply -f k8s/

# 6. Monitor rollout
kubectl rollout status deployment/finvista-assistant -n finvista

# 7. Get the LoadBalancer URL
kubectl get service finvista-service -n finvista
```

---

## Phase 4 – CI/CD (GitHub Actions)

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `AWS_ACCESS_KEY_ID` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |

### Pipeline Stages

```
Push to main
    │
    ▼
pytest (unit tests + coverage)
    │
    ▼
docker build + push to ECR
    │
    ▼
kubectl apply (K8s manifests)
    │
    ▼
kubectl set image (rolling update)
    │
    ▼
kubectl rollout status (verify)
```

---

## Running Tests

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=app
```

---

## Key Technologies

| Component | Technology |
|---|---|
| LLM | Google Gemini 1.5 Flash |
| Embeddings | Google `models/embedding-001` |
| Vector DB | ChromaDB (persistent) |
| PDF Parsing | PyMuPDF (fitz) |
| Text Splitting | LangChain RecursiveCharacterTextSplitter |
| UI | Streamlit |
| Container | Docker (multi-stage) |
| Orchestration | Kubernetes (EKS) |
| CI/CD | GitHub Actions |

---

## Troubleshooting

**`GEMINI_API_KEY` not set** → Set it in `.env` or as a K8s secret.

**ChromaDB permission error on K8s** → Ensure PVC is bound: `kubectl get pvc -n finvista`

**Pod CrashLoopBackOff** → Check logs: `kubectl logs -l app=finvista-assistant -n finvista`

**Slow embeddings** → Gemini free tier has rate limits; reduce batch size or upgrade plan.
