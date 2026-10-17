# CivicFix Backend

FastAPI + SQLAlchemy backend for the CivicFix civic issue reporting platform.

## Local setup

```bash
cd backend

# Create virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy env file (already filled in at root)
# The app reads ../.env.txt automatically

# Start dev server
uvicorn app.main:app --reload
```

The server starts at **http://localhost:8000**

- API docs (Swagger): http://localhost:8000/docs
- Health check:       http://localhost:8000/health

## Database

Uses **Neon PostgreSQL** (serverless). Tables are created automatically on startup via `Base.metadata.create_all()` — no migrations needed for the hackathon.

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string with `?sslmode=require` |
| `JWT_SECRET` | Random secret for signing JWTs |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary account |
| `CLOUDINARY_API_KEY` | Cloudinary key |
| `CLOUDINARY_API_SECRET` | Cloudinary secret |
| `GEMINI_API_KEY` | Google Gemini (optional — falls back to keyword rules) |
| `FRONTEND_URL` | CORS origin, e.g. `http://localhost:5173` |

## Deployment (Render)

1. New Web Service → connect GitHub repo
2. Root directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all env vars in the Render dashboard
