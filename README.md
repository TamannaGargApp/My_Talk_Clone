# AI Voice Agent — Meet My AI Twin

A voice-enabled conversational AI application built with **FastAPI, Google Gemini, MongoDB Atlas, uv, and vanilla HTML/CSS/JavaScript**. Visitors can ask questions using text or their microphone and listen to spoken answers. Guest access is available without registration; signed-in users can save, revisit, continue, and manage their conversations.

**Live demo:** https://mytalkclone.vercel.app/

## Features

- Text chat powered by Google Gemini
- Browser speech recognition for voice input and speech synthesis for spoken replies
- Guest chat without registration (guest messages are not stored)
- Email/password registration and sign-in, plus Google OAuth
- JWT-authenticated, user-specific conversation storage in MongoDB Atlas
- Chat history sidebar: browse sessions, reopen previous messages, continue a conversation, start a new chat, and delete sessions
- Responsive static frontend, with FastAPI serving the backend API

## 1. Requirements

- **Python 3.14** (requested setup target; check that all pinned dependencies support this version before installation)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- MongoDB Atlas cluster and database user
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Optional Google Cloud OAuth 2.0 **Web application** credentials

## 2. Backend setup (Windows PowerShell)

Run the following from the project root:

```powershell
cd backend
uv lock
uv venv .venv --python 3.14
.venv\Scripts\Activate.ps1
uv sync
Copy-Item .env.example .env
```

> If `uv lock` or `uv sync` reports Python-version incompatibilities, check `backend/pyproject.toml` and the supported versions of its dependencies. Do not change the project's `requires-python` setting or force incompatible packages without testing. If necessary, use a compatible Python version such as 3.12 and recreate the environment.

Edit `backend/.env` with your own values. Do **not** commit `.env` or publish API keys, OAuth secrets, MongoDB credentials, or JWT secrets.

Generate a strong JWT secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `JWT_SECRET` in `backend/.env`.

Example local configuration (replace placeholders with your credentials):

```dotenv
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5500
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
MONGODB_URI=your_mongodb_atlas_connection_string
MONGODB_DATABASE=voice_agent
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_available_gemini_model
JWT_SECRET=your_generated_secret
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

Start the backend:

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

Check [http://localhost:8000/health](http://localhost:8000/health) and the interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

**Lockfile:** `uv lock` generates or updates `backend/uv.lock`. Commit the lockfile to Git before deploying. `uv sync` installs dependencies into the environment and may update it to match the project configuration.

## 3. Frontend setup

In a second terminal, from the project root:

```powershell
cd frontend
python -m http.server 5500
```

Open **http://localhost:5500/** (the root URL, without `/index.html`). The frontend is plain HTML/CSS/JavaScript, so no Node.js build is required.

Set `frontend/config.js` to use your local API URL if needed:

```javascript
window.API_BASE_URL = 'http://localhost:8000';
```

If you serve the frontend from another origin, add that origin to `CORS_ORIGINS` in `backend/.env`, then restart FastAPI.

## 4. Google sign-in

Create an OAuth 2.0 client of type **Web application** in [Google Cloud Console](https://console.cloud.google.com/apis/credentials). Add the local authorized redirect URI:

```text
http://localhost:8000/api/auth/google/callback
```

Add the client ID and secret to `backend/.env`. The backend starts authorization at `/api/auth/google/start`, receives Google's callback, and sends the browser to the frontend with a short-lived, single-use exchange code. The frontend exchanges that code for an application JWT.

Never expose the Google client secret in frontend code. Google sign-in is optional; email/password login and guest access can work independently.

For the current Vercel-proxied production setup, configure the exact HTTPS callback URL in **both** Google Cloud Console and Render:

```dotenv
GOOGLE_REDIRECT_URI=https://mytalkclone.vercel.app/api/auth/google/callback
FRONTEND_URL=https://mytalkclone.vercel.app
CORS_ORIGINS=https://mytalkclone.vercel.app
```

The Google callback is routed through Vercel's `/api/*` proxy to the Render backend. Keep `GOOGLE_REDIRECT_URI` identical to the URI registered in Google Cloud Console, including its scheme and path. The post-login frontend redirect should target `/#oauth=...`, not `/index.html#oauth=...`.

## 5. Conversation history

Authenticated chat messages are stored in MongoDB's `conversations` collection and associated with the signed-in user's ID and a `session_id`. The chat history interface can list previous sessions, display messages in chronological order, resume a session, and delete it. Only the authenticated owner should be able to retrieve or delete their sessions.

Guest conversations are not persisted. A new chat starts a new session; reopening an existing conversation reuses its session ID. History persists across sign-ins because it is stored on the server, not only in browser storage.

## 6. Deployment

### Backend — Render

1. Push the repository to GitHub, including `backend/uv.lock`.
2. Create a Python Web Service with **Root Directory** set to `backend`.
3. **Build command:**

   ```bash
   pip install uv && uv sync --frozen --no-dev
   ```

4. **Start command:**

   ```bash
   uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

5. Configure Render environment variables based on `backend/.env.example`. Use production HTTPS URLs and real secrets; never upload the `.env` file. Ensure MongoDB Atlas permits the backend's network access, restricting it where feasible.

### Frontend — Vercel

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `frontend` and **Framework Preset** to `Other`. No frontend build command is required.
3. Keep the existing `frontend/vercel.json` rewrite that forwards `/api/:path*` to your Render backend. Do not replace its destination with a placeholder.
4. Set `frontend/config.js` to use the intended API origin. If using same-origin `/api/*` rewrites, configure the frontend to call the Vercel origin; if using Render directly, configure CORS appropriately.
5. Set the production Google OAuth redirect URI in Render and Google Cloud Console to the exact URL shown above.
6. Deploy and test guest chat, registration, email login, Google sign-in, conversation history, new chat, delete, microphone input, and speech playback.

Use HTTPS in production for microphone permissions. Browser speech recognition support varies; Chromium-based browsers commonly provide the best support.

## 7. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health check |
| POST | `/api/auth/register` | Create an account |
| POST | `/api/auth/login` | Sign in with email/password |
| GET | `/api/auth/me` | Retrieve current authenticated user |
| GET | `/api/auth/google/start` | Begin Google OAuth |
| GET | `/api/auth/google/callback` | Receive Google OAuth callback |
| POST | `/api/auth/google/exchange` | Exchange one-time code for JWT |
| POST | `/api/chat` | Ask a question; guest access allowed |
| GET | `/api/chat/history` | Retrieve authenticated message history |
| GET | `/api/chat/sessions` | List authenticated user's conversation sessions |
| GET | `/api/chat/sessions/{session_id}` | Retrieve a session's messages |
| DELETE | `/api/chat/sessions/{session_id}` | Delete an owned conversation session |

> The session endpoints require the updated chat-history backend implementation. If using an older `chat.py`, add those routes before relying on the sidebar.

## 8. Configuration and security notes

- Customize `backend/app/prompts/personality_prompt.py` with accurate, verified information for the AI representative.
- `GEMINI_MODEL` is configurable. Choose a model available to your Gemini API account and monitor quota usage.
- Guest messages are intentionally not persisted and do not have server-side previous-turn context.
- Public guest chat needs rate limiting, abuse prevention, request budgets, and monitoring before broader production use.
- JWTs are stored in browser `sessionStorage` in this implementation. For higher-security applications, consider a backend-for-frontend or carefully designed secure HTTP-only session-cookie approach.
- Apply suitable data retention and deletion policies for stored conversations.
- The AI should acknowledge information it does not know rather than invent personal details or achievements.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript, Browser Speech APIs |
| Backend | Python, FastAPI, Uvicorn |
| AI | Google Gemini |
| Database | MongoDB Atlas / PyMongo |
| Authentication | JWT, password-based login, Google OAuth via Authlib |
| Dependency management | uv |
| Hosting | Vercel (frontend), Render (backend) |
