# 🚀 NeuralQuest — Render Deployment Guide

This guide describes how to deploy the **NeuralQuest (Gamified RAG Platform)** to [Render.com](https://render.com).

---

## 🛠️ Prerequisites
1. A GitHub account with this repository pushed.
2. A free account on [Render.com](https://render.com).
3. A Google Gemini API key.

---

## ⚡ Deployment Options

### Option 1: Automatic Blueprint (Recommended)
1. In Render, go to **Blueprints** → **New Blueprint Instance**.
2. Connect your GitHub repository: `Meera33soundharya/neuralquest`.
3. In the environment variables prompt, enter your `GEMINI_API_KEY`.
4. Click **Apply**.
5. Render will automatically build dependencies, collect static files, run database migrations, and launch Gunicorn on `0.0.0.0:$PORT`.

---

### Option 2: Manual Web Service
1. Click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Name**: `neuralquest-rag`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**:
     ```bash
     gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
     ```
4. Under **Environment Variables**, add:
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `*`
   - `USE_SQLITE`: `true`
   - `SECRET_KEY`: *(Any long random string or let Render generate)*
   - `GEMINI_API_KEY`: *(Your Google Gemini API Key)*
5. Click **Create Web Service**.

---

## 📦 What's Included
- `render.yaml`: Infrastructure-as-code for Render.
- `Procfile`: Gunicorn WSGI startup configuration.
- `Dockerfile`: Container image definition if deploying as a Docker Web Service on Render or Railway.
- `whitenoise`: Configured in Django middleware to serve all CSS, JS, and font assets in production without requiring an external S3 bucket.

