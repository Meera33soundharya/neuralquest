# 🎮 NeuralQuest — AI Knowledge Gaming & Enterprise RAG Arena

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Meera33soundharya/neuralquest)

A full-stack **AI-Powered Knowledge Gaming & Retrieval-Augmented Generation (RAG) platform** built with Django REST Framework, ChromaDB, FastEmbed, and Google Gemini AI.

Transform static PDF documentation into an interactive knowledge assistant and gamified learning arena with dynamic AI quizzes, XP progression, leaderboards, and learning analytics.

---

## 🚀 Key Features

### 🧠 Grounded RAG Chatbot
- **Document Ingestion**: Upload PDF manuals, guides, or course materials.
- **Fast Multi-Threaded Embeddings**: Local high-speed vector embeddings via FastEmbed (`snowflake-arctic-embed-xs`).
- **ChromaDB Vector Store**: HNSW-indexed low-latency semantic chunk retrieval.
- **In-Memory Query Caching**: Instant (<1ms) response times for cached inquiries.
- **Sourced Answers**: Full page and chunk citations for every AI response.

### 🎯 Gamified Learning Engine
- **Multi-Mode Quiz Generator**: Automatically converts document context into:
  - ⚔️ **Quiz Battle** (4-option Multiple Choice)
  - ⏱️ **Time Challenge** (Fast-paced speed tests)
  - ⚖️ **True / False** (Statement verification)
  - 🗂️ **Flashcard Arena** (Concept mastery)
- **Mingled / Shuffled Options**: Options (`A`, `B`, `C`, `D`) are dynamically randomized across all questions so answers are never predictable.
- **XP Progression & Levels**: Earn XP on correct answers, level up player profiles.
- **Leaderboards & Badges**: Real-time rank tracking and achievement unlocks.
- **Learning Analytics**: Track overall accuracy, game history, and study progress.

---

## ⚡ 1-Click Deployment to Render

Click the button below to deploy this application directly to Render:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Meera33soundharya/neuralquest)

### Environment Variables on Render
- `USE_SQLITE`: `true`
- `ALLOWED_HOSTS`: `*`
- `DEBUG`: `False`
- `GEMINI_API_KEY`: *(Your Google Gemini API Key)*

---

## 💻 Local Quickstart

```bash
# 1. Clone repository
git clone https://github.com/Meera33soundharya/neuralquest.git
cd neuralquest

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows (or: source venv/bin/activate on Linux/Mac)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Launch server
python manage.py runserver
```

Open [http://localhost:8000/](http://localhost:8000/) in your browser.
