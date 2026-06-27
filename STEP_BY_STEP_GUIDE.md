# FinVista Capital – Complete Step-by-Step Setup Guide

---

## OVERVIEW: What You Will Do

```
STEP 1  Get Gemini API Key (Google)
STEP 2  Set up your laptop (VS Code, Python, Git, Docker, AWS CLI, kubectl)
STEP 3  Run the app locally in VS Code
STEP 4  Prepare your PDF documents (Knowledge Base)
STEP 5  Create AWS S3 bucket (document storage backup)
STEP 6  Create AWS ECR repository (Docker image storage)
STEP 7  Create AWS EKS cluster (Kubernetes)
STEP 8  Build and push Docker image to ECR
STEP 9  Deploy to Kubernetes (EKS)
STEP 10 Set up GitHub Actions CI/CD pipeline
```

---

## STEP 1 — Get Your Gemini API Key (FREE)

1. Open browser → go to **https://aistudio.google.com**
2. Sign in with your Google account
3. Click **"Get API key"** (top left)
4. Click **"Create API key"**
5. Select **"Create API key in new project"**
6. Copy the key — it looks like: `AIzaSyD......................`
7. Save it safely — you will use it in VS Code and AWS

> **Free tier limits:** 15 requests/minute, 1 million tokens/day — enough for this project.

---

## STEP 2 — Set Up Your Laptop

### 2A. Install VS Code
1. Go to **https://code.visualstudio.com**
2. Download for your OS (Windows/Mac/Linux)
3. Install it
4. Open VS Code → Install extension: **Python** (by Microsoft)

### 2B. Install Python 3.11
- **Windows:** https://www.python.org/downloads/ → Download Python 3.11.x → Install (check "Add to PATH")
- **Mac:** `brew install python@3.11`
- **Linux (Ubuntu):** `sudo apt install python3.11 python3.11-venv`

Verify: open terminal → `python --version` → should show `Python 3.11.x`

### 2C. Install Git
- **Windows:** https://git-scm.com/download/win
- **Mac:** `brew install git`
- **Linux:** `sudo apt install git`

### 2D. Install Docker Desktop
1. Go to **https://www.docker.com/products/docker-desktop**
2. Download for your OS
3. Install and start Docker Desktop
4. Verify: `docker --version`

### 2E. Install AWS CLI
- **Windows:** https://aws.amazon.com/cli/ → Download MSI installer
- **Mac:** `brew install awscli`
- **Linux:** `sudo apt install awscli` or follow https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html

Verify: `aws --version`

### 2F. Install kubectl
- **Windows:** `winget install Kubernetes.kubectl`
- **Mac:** `brew install kubectl`
- **Linux:** 
  ```bash
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
  chmod +x kubectl && sudo mv kubectl /usr/local/bin/
  ```

Verify: `kubectl version --client`

### 2G. Install eksctl (EKS cluster tool)
- **Windows:** `winget install eksctl`
- **Mac:** `brew install eksctl`
- **Linux:**
  ```bash
  curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
  sudo mv /tmp/eksctl /usr/local/bin
  ```

---

## STEP 3 — Run the App Locally in VS Code

### 3A. Open the project
1. Open VS Code
2. `File → Open Folder` → select the `finvista` folder you downloaded

### 3B. Open VS Code Terminal
Press `` Ctrl+` `` (backtick) to open terminal inside VS Code

### 3C. Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3.11 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### 3D. Install dependencies
```bash
pip install -r requirements.txt
```
This takes 3–5 minutes. You will see packages installing.

### 3E. Create your .env file
```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Now open `.env` in VS Code and edit it:
```
GEMINI_API_KEY=AIzaSyD....your_actual_key_here....
```

### 3F. Run the app
```bash
streamlit run app/streamlit_app.py
```

Browser will open automatically at **http://localhost:8501**

### 3G. Test it works
1. In the sidebar, your API key is pre-filled from `.env`
2. Click **"Browse files"** and upload a PDF
3. Wait for "✅ X chunks indexed"
4. Go to Chat tab → type a question → click **Ask**

---

## STEP 4 — What PDF Documents to Upload (Knowledge Base)

### Documents to put in your knowledge base:

| Document Type | Example Filenames | Where to get them |
|---|---|---|
| Annual Reports | `annual_report_2023.pdf` | Company investor relations websites |
| Analyst Reports | `equity_research_Q3.pdf` | Financial data providers |
| Compliance Manuals | `compliance_manual_2024.pdf` | Internal company docs |
| Investment Guidelines | `investment_policy.pdf` | Internal company docs |
| Market Research | `market_outlook_2024.pdf` | Bloomberg, Reuters, etc. |
| Risk Frameworks | `risk_assessment_guide.pdf` | Internal or regulatory bodies |

### For the demo/capstone — use these free sources:
1. **Tesla Annual Report:** https://ir.tesla.com → Annual Reports → Download PDF
2. **Apple 10-K:** https://investor.apple.com → SEC Filings → 10-K
3. **RBI Guidelines:** https://www.rbi.org.in → Publications → Free PDFs
4. **SEBI Circulars:** https://www.sebi.gov.in → Legal Framework → Circulars

### Upload through the app:
- Use the Streamlit sidebar → "Browse files"
- OR upload to S3 (next step) for backup

---

## STEP 5 — Create AWS S3 Bucket (Document Storage)

### 5A. Create AWS Account (if you don't have one)
1. Go to **https://aws.amazon.com**
2. Click **"Create an AWS Account"**
3. Fill in email, password, account name
4. Enter payment info (free tier — you won't be charged for this project)
5. Verify phone number

### 5B. Create IAM User (for programmatic access)
1. Log into **AWS Console** → search **IAM** → click IAM
2. Click **Users → Create user**
3. Username: `finvista-user`
4. Click **Next → Attach policies directly**
5. Select these policies:
   - `AmazonS3FullAccess`
   - `AmazonECR_FullAccess` (or `AmazonEC2ContainerRegistryFullAccess`)
   - `AmazonEKSClusterPolicy`
   - `AmazonEKSWorkerNodePolicy`
   - `IAMFullAccess`
6. Click **Create user**
7. Click on the user → **Security credentials** tab → **Create access key**
8. Select **CLI** → Next → Create
9. **COPY BOTH:** Access Key ID and Secret Access Key — you only see them once!

### 5C. Configure AWS CLI on your laptop
```bash
aws configure
```
Enter when prompted:
```
AWS Access Key ID: AKIA...your key...
AWS Secret Access Key: your_secret_key
Default region name: us-east-1
Default output format: json
```

Verify: `aws sts get-caller-identity` — should show your account info

### 5D. Create S3 Bucket
```bash
aws s3 mb s3://finvista-documents-yourname --region us-east-1
```
Replace `yourname` with something unique (S3 bucket names must be globally unique).

### 5E. Upload your PDF documents to S3
```bash
# Upload a single file
aws s3 cp annual_report_2023.pdf s3://finvista-documents-yourname/documents/

# Upload all PDFs from a folder
aws s3 cp ./documents/ s3://finvista-documents-yourname/documents/ --recursive --include "*.pdf"
```

### 5F. Verify upload
```bash
aws s3 ls s3://finvista-documents-yourname/documents/
```

> **Note:** S3 is used as a backup/archive for your raw PDFs. The app processes PDFs directly — it doesn't read from S3 automatically. You can extend it to do so, but for this capstone, upload to S3 for storage and also upload via the Streamlit UI for indexing.

---

## STEP 6 — Create AWS ECR Repository (Docker Image Storage)

```bash
# Create the repository
aws ecr create-repository \
  --repository-name finvista-assistant \
  --region us-east-1

# Save the URI — you will need it
aws ecr describe-repositories \
  --repository-names finvista-assistant \
  --query 'repositories[0].repositoryUri' \
  --output text
```

Output will look like: `123456789.dkr.ecr.us-east-1.amazonaws.com/finvista-assistant`

**Save this URI** — replace `YOUR_ECR_REGISTRY` everywhere in the files.

---

## STEP 7 — Create AWS EKS Cluster

> This takes 15–20 minutes. Run it and wait.

```bash
eksctl create cluster \
  --name finvista-cluster \
  --region us-east-1 \
  --nodegroup-name finvista-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed
```

### Verify cluster is ready:
```bash
kubectl get nodes
```
Should show 2 nodes with status `Ready`.

### Update kubeconfig:
```bash
aws eks update-kubeconfig --name finvista-cluster --region us-east-1
```

---

## STEP 8 — Build and Push Docker Image to ECR

### 8A. Set your ECR URI as a variable
```bash
# Replace with YOUR actual ECR URI from Step 6
ECR_URI="123456789.dkr.ecr.us-east-1.amazonaws.com/finvista-assistant"
```

### 8B. Login to ECR
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI
```
Should see: `Login Succeeded`

### 8C. Build Docker image
```bash
# Make sure you're in the finvista project folder
cd finvista

docker build -t finvista-assistant:latest .
```
Takes 5–10 minutes on first build.

### 8D. Tag and push to ECR
```bash
docker tag finvista-assistant:latest $ECR_URI:latest
docker push $ECR_URI:latest
```

### 8E. Verify image is in ECR
```bash
aws ecr describe-images \
  --repository-name finvista-assistant \
  --region us-east-1
```

---

## STEP 9 — Deploy to Kubernetes (EKS)

### 9A. Update deployment file with your ECR image URI
Open `k8s/04-deployment.yaml` in VS Code.
Find this line:
```
image: YOUR_ECR_REGISTRY/finvista-assistant:latest
```
Replace with your actual ECR URI:
```
image: 123456789.dkr.ecr.us-east-1.amazonaws.com/finvista-assistant:latest
```

### 9B. Create the Kubernetes secret for your Gemini API key
```bash
# Encode your API key in base64
echo -n "AIzaSyD....your_gemini_key...." | base64
```
Copy the output (looks like `QUl6YVN5RC4u...`)

Open `k8s/02-secret.yaml` in VS Code:
```yaml
data:
  GEMINI_API_KEY: QUl6YVN5RC4u...paste_your_base64_here...
```

### 9C. Apply all Kubernetes manifests (in order)
```bash
kubectl apply -f k8s/01-namespace-configmap.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-pvc.yaml
kubectl apply -f k8s/04-deployment.yaml
kubectl apply -f k8s/05-service-ingress.yaml
kubectl apply -f k8s/06-hpa.yaml
```

Or apply everything at once:
```bash
kubectl apply -f k8s/
```

### 9D. Check deployment status
```bash
# Watch pods start up (press Ctrl+C to stop watching)
kubectl get pods -n finvista -w

# Check deployment
kubectl get deployment -n finvista

# Check service (wait for EXTERNAL-IP)
kubectl get service finvista-service -n finvista
```

### 9E. Get the app URL
```bash
kubectl get service finvista-service -n finvista
```
Look for `EXTERNAL-IP` column. It will look like:
`abc123.us-east-1.elb.amazonaws.com`

Open that in your browser — your app is live!

### 9F. Useful kubectl commands for troubleshooting
```bash
# See logs from a pod
kubectl logs -l app=finvista-assistant -n finvista

# Describe a pod (shows errors)
kubectl describe pod -l app=finvista-assistant -n finvista

# Check HPA (autoscaler)
kubectl get hpa -n finvista

# Delete everything (to start fresh)
kubectl delete namespace finvista
```

---

## STEP 10 — Set Up GitHub Actions CI/CD

### 10A. Push code to GitHub
1. Go to **https://github.com** → Sign in → New repository
2. Name it `finvista-assistant` → Private → Create
3. In VS Code terminal:
```bash
git init
git add .
git commit -m "Initial commit: FinVista RAG application"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/finvista-assistant.git
git push -u origin main
```

### 10B. Add GitHub Secrets
1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Click **"New repository secret"** for each:

| Secret Name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key (e.g. `AIzaSyD...`) |
| `AWS_ACCESS_KEY_ID` | Your AWS Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | Your AWS Secret Access Key |

### 10C. Trigger the pipeline
```bash
# Make any small change
echo "# FinVista" >> README.md
git add README.md
git commit -m "Trigger CI/CD pipeline"
git push
```

### 10D. Watch the pipeline run
1. Go to GitHub repo → **Actions** tab
2. You will see the workflow running with 3 jobs:
   - ✅ Run Tests
   - ✅ Build & Push to ECR
   - ✅ Deploy to EKS

### 10E. Pipeline runs automatically on every push to main
Any future code change → push to GitHub → pipeline auto-runs → new version deployed.

---

## QUICK REFERENCE: All Commands in Order

```bash
# ── Local Dev ──────────────────────────────────────────────────────────
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env with your Gemini key
streamlit run app/streamlit_app.py

# ── Tests ──────────────────────────────────────────────────────────────
pytest tests/ -v

# ── Docker ─────────────────────────────────────────────────────────────
docker build -t finvista-assistant .
docker run -p 8501:8501 -e GEMINI_API_KEY=your_key finvista-assistant

# ── AWS Setup ──────────────────────────────────────────────────────────
aws configure
aws s3 mb s3://finvista-documents-yourname --region us-east-1
aws ecr create-repository --repository-name finvista-assistant --region us-east-1
eksctl create cluster --name finvista-cluster --region us-east-1 \
  --nodegroup-name finvista-nodes --node-type t3.medium --nodes 2 --managed

# ── Push Docker to ECR ─────────────────────────────────────────────────
ECR_URI=$(aws ecr describe-repositories --repository-names finvista-assistant \
  --query 'repositories[0].repositoryUri' --output text)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI
docker tag finvista-assistant:latest $ECR_URI:latest
docker push $ECR_URI:latest

# ── Deploy to K8s ──────────────────────────────────────────────────────
aws eks update-kubeconfig --name finvista-cluster --region us-east-1
kubectl apply -f k8s/
kubectl get service finvista-service -n finvista   # get URL

# ── Git / CI-CD ────────────────────────────────────────────────────────
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/finvista-assistant.git
git push -u origin main
```

---

## COST ESTIMATE (AWS Free Tier)

| Service | Usage | Estimated Cost |
|---|---|---|
| EKS Cluster | $0.10/hour | ~$2.40/day |
| EC2 t3.medium (2 nodes) | $0.0416/hour each | ~$2/day |
| S3 Storage | First 5GB free | $0 |
| ECR Storage | First 500MB free | $0 |
| Gemini API | Free tier (15 rpm) | $0 |
| **Total (demo only)** | | **~$4.50/day** |

> **To avoid charges after the demo:** run `eksctl delete cluster --name finvista-cluster --region us-east-1`

---

## TROUBLESHOOTING

| Problem | Solution |
|---|---|
| `GEMINI_API_KEY not set` | Check `.env` file or K8s secret |
| `No module named 'fitz'` | `pip install PyMuPDF` |
| `chromadb permission error` | Check PVC is bound: `kubectl get pvc -n finvista` |
| `ImagePullBackOff` in K8s | ECR URI wrong in `04-deployment.yaml` |
| `CrashLoopBackOff` | `kubectl logs -l app=finvista-assistant -n finvista` |
| Docker build fails | Ensure Docker Desktop is running |
| `kubectl: command not found` | Reinstall kubectl (Step 2F) |
| EKS nodes NotReady | Wait 5 more minutes, cluster is still starting |
