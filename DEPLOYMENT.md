# TravelPilot Deployment Guide

This guide provides instructions on how to build and deploy the TravelPilot application. You can choose between:
1. **Option A: Free Services (Render + Vercel)** — 100% free hosting using Vercel (frontend) and Render (backend).
2. **Option B: Google Cloud Platform (Cloud Run)** — Native GCP deployment with Cloud Run and Secret Manager.

---

## Option A: Deploying with Free Services (Vercel & Render)

This option is completely free, requires no credit card verification for standard features, and is ideal for developer testing, demoing, and PromptWars evaluations.

### 1. Database Setup (Optional - Google Firestore Free Tier)
To persist user sessions in production, we use Google Firestore's free tier (up to 50k reads and 20k writes per day).
1. Go to the [Firebase Console](https://console.firebase.google.com/) and create or select your project.
2. Initialize **Firestore Database** in **Native Mode**.
3. Navigate to **Project Settings > Service Accounts**.
4. Click **Generate New Private Key** to download the credentials JSON file.
5. Keep this JSON content handy; you will paste it as an environment variable in Render.
*Note: If you do not want to set up a database, you can set `USE_FIRESTORE=false` in the backend environment variables to run using an automatic in-memory fallback session store.*

### 2. Backend Deployment on Render (FastAPI)
Render provides a completely free tier for hosting web services.
1. Sign up/log in to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New > Web Service** and connect your GitHub repository.
3. Apply the following settings:
   - **Name**: `travelpilot-backend`
   - **Region**: Select a region close to your target users.
   - **Branch**: `main` (or your active branch)
   - **Runtime**: `Python`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
4. Under the **Variables** (Environment Variables) section, add the following:
   - `GEMINI_API_KEY`: Your Gemini API Key (obtained from Google AI Studio).
   - `USE_FIRESTORE`: `true` (if using Firestore) or `false` (to run using the in-memory fallback).
   - `FIREBASE_PROJECT_ID`: Your GCP/Firebase Project ID.
   - `GOOGLE_CREDENTIALS_JSON`: The exact, full JSON string from your downloaded service account key file (only required if `USE_FIRESTORE` is `true`).
   - `ALLOWED_ORIGINS`: Set to `*` initially, or update to your frontend Vercel URL once deployed to restrict CORS.
5. Click **Create Web Service**. Wait for the build and deployment to complete. Copy your backend service URL (e.g., `https://travelpilot-backend.onrender.com`).

> [!WARNING]
> **Render Cold Starts**: Render's free tier web services spin down after 15 minutes of inactivity. When a request comes in after spin-down, it can take ~50 seconds to boot up.

---

### 3. Frontend Deployment on Vercel (Next.js)
Vercel is the optimized hosting provider for Next.js, offering a 100% free Hobby tier.
1. Sign up/log in to the [Vercel Dashboard](https://vercel.com/).
2. Click **Add New > Project** and import your GitHub repository.
3. Configure the project:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `frontend`
   - **Build & Development Settings**: Keep defaults.
4. Under the **Environment Variables** section, add:
   - `NEXT_PUBLIC_API_URL`: The URL of your Render backend (e.g., `https://travelpilot-backend.onrender.com`). *Ensure there is no trailing slash.*
5. Click **Deploy**. Vercel will build and host your Next.js frontend, providing a URL (e.g., `https://travelpilot-frontend.vercel.app`).

---

## Option B: Deploying to Google Cloud Run (Production GCP)

This option deploys both services natively onto Google Cloud Run, utilizing Google Secret Manager for secure key storage.

### Prerequisites
1. A **Google Cloud Platform (GCP)** project.
2. The **Google Cloud CLI (`gcloud`)** installed and authenticated (`gcloud auth login`).
3. Firestore enabled in Native Mode in your GCP project.

### 1. Enable Required GCP APIs
Enable the necessary APIs for Cloud Run, Cloud Build, Secret Manager, and Firestore:
```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    firestore.googleapis.com
```

### 2. Store Secrets in Secret Manager
We store the `GEMINI_API_KEY` securely in Secret Manager so it can be mounted directly into the Cloud Run container.
1. Create the Secret:
   ```bash
   gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
   ```
2. Add the Secret version:
   ```bash
   echo -n "YOUR_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-
   ```
3. Grant access to the default Cloud Run Service Account:
   ```bash
   gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
       --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

### 3. Deploy Backend to Cloud Run
Run these commands from the `backend/` directory:
```bash
cd backend

gcloud run deploy travelpilot-backend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --max-instances 3 \
    --cpu 1 \
    --memory 1Gi \
    --set-env-vars="USE_FIRESTORE=true,FIREBASE_PROJECT_ID=[YOUR_FIREBASE_PROJECT_ID],ENABLE_CLOUD_LOGGING=true,ALLOWED_ORIGINS=https://[YOUR-FRONTEND-URL]" \
    --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

### 4. Deploy Frontend to Cloud Run
Run these commands from the `frontend/` directory:
```bash
cd ../frontend

gcloud run deploy travelpilot-frontend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --max-instances 3 \
    --cpu 1 \
    --memory 1Gi \
    --set-env-vars="NEXT_PUBLIC_API_URL=https://[YOUR-BACKEND-URL]"
```
