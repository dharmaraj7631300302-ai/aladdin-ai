import os
import asyncio
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AladdinAI")

app = FastAPI(title="Aladdin AI Backend", version="1.0")

# Security: CORS for Frontend (Vercel/Bolt)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Required for OAuth session state
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "super-secret-aladdin-key"))

# ==========================================
# 2. DATABASE & LONG-TERM MEMORY (SQLite)
# ==========================================
DATABASE_URL = "sqlite:///./aladdin_memory.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    key = Column(String, index=True)
    value = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class PendingAction(Base):
    """Human-in-the-loop task queue"""
    __tablename__ = "pending_actions"
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String) # e.g., 'post_video'
    payload = Column(Text)       # JSON string of task details
    status = Column(String, default="pending") # pending, approved, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. OAUTH 2.0 INTEGRATION (Google & Meta)
# ==========================================
config = Config(environ=os.environ)
oauth = OAuth(config)

oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID", "stub_client_id"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "stub_client_secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/youtube.upload'}
)

@app.get("/auth/{provider}")
async def login(provider: str, request: Request):
    redirect_uri = request.url_for('auth_callback', provider=provider)
    client = oauth.create_client(provider)
    return await client.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback/{provider}")
async def auth_callback(provider: str, request: Request):
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    # In production: Securely store `token['access_token']` in DB linked to user
    return {"message": f"Successfully authenticated with {provider}", "token_type": token.get("token_type")}

# ==========================================
# 4. AGENTIC TOOLBOX
# ==========================================
def tool_web_search(query: str) -> str:
    """Scrape web for real-time data."""
    try:
        # Example using DuckDuckGo HTML (Simplified for demonstration)
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(f"https://html.duckduckgo.com/html/?q={query}", headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = soup.find_all('a', class_='result__snippet')
        snippets = [r.text for r in results[:3]]
        return " | ".join(snippets) if snippets else "No results found."
    except Exception as e:
        return f"Search failed: {str(e)}"

def tool_generate_asset(text_overlay: str):
    """Auto-generate creative banner with Pillow (Stub for DALL-E/Flux)."""
    os.makedirs("assets", exist_ok=True)
    img = Image.new('RGB', (800, 400), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((50, 180), text_overlay, fill=(255, 255, 0))
    filepath = f"assets/banner_{datetime.now().strftime('%Y%timestamp')}.png"
    img.save(filepath)
    return filepath

# ==========================================
# 5. AUTONOMOUS BACKGROUND ENGINE & HITL
# ==========================================
async def execute_social_post(task_id: int, db: Session):
    """Background task with Network Retry Logic."""
    task = db.query(PendingAction).filter(PendingAction.id == task_id).first()
    if not task: return
    
    task.status = "processing"
    db.commit()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"[Task {task_id}] Fetching from Google Drive... (Mock)")
            await asyncio.sleep(1) # Simulate API latency
            
            logger.info(f"[Task {task_id}] Uploading to YouTube & Meta... (Mock)")
            await asyncio.sleep(2) # Simulate API upload
            
            # Simulate random network drop
            # if random.random() < 0.3: raise ConnectionError("Network dropped during Meta Graph API upload.")
            
            task.status = "completed"
            db.commit()
            logger.info(f"[Task {task_id}] Successfully posted.")
            return
            
        except Exception as e:
            logger.error(f"[Task {task_id}] Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                task.status = "failed"
                task.payload += f" | Error: {str(e)}"
                db.commit()
            await asyncio.sleep(2 ** attempt) # Exponential backoff

# ==========================================
# 6. API ENDPOINTS (Frontend Interfaces)
# ==========================================
class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    msg = req.message.lower()
    response_text = ""

    # 1. Long Term Memory Recall
    user_prefs = db.query(Memory).filter(Memory.user_id == req.user_id).all()
    memory_context = {m.key: m.value for m in user_prefs}

    # 2. Agentic Routing Logic (Rule-based stub replacing LLM for brevity)
    if "remember" in msg:
        # e.g., "Remember that my brand color is blue"
        db.add(Memory(user_id=req.user_id, key="brand_color", value="blue"))
        db.commit()
        response_text = "I've saved that to my long-term memory."

    elif "search" in msg:
        query = msg.replace("search", "").strip()
        result = tool_web_search(query)
        response_text = f"Here is what I found on the web: {result}"

    elif "generate banner" in msg:
        path = tool_generate_asset("Aladdin AI Generated")
        response_text = f"I generated the creative asset and saved it locally at {path}."

    elif "post video" in msg:
        # HUMAN-IN-THE-LOOP TRIGGER
        new_task = PendingAction(action_type="social_post", payload='{"drive_file": "vid_123", "platforms": ["youtube", "instagram"]}')
        db.add(new_task)
        db.commit()
        response_text = "I have staged the video from Google Drive for posting. It is waiting for your approval in the queue."

    else:
        # Standard chat response
        brand_color = memory_context.get("brand_color", "default")
        response_text = f"I am Aladdin AI. Your brand color is {brand_color}. Ask me to search the web, generate a banner, or post a video!"

    return {"reply": response_text, "audio_supported": True}

@app.get("/api/actions/pending")
def get_pending_actions(db: Session = Depends(get_db)):
    actions = db.query(PendingAction).filter(PendingAction.status == "pending").all()
    return [{"id": a.id, "type": a.action_type, "payload": a.payload} for a in actions]

@app.post("/api/actions/{action_id}/approve")
def approve_action(action_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(PendingAction).filter(PendingAction.id == action_id).first()
    if not task or task.status != "pending":
        raise HTTPException(status_code=400, detail="Task not found or not pending.")
    
    task.status = "approved"
    db.commit()
    
    # Trigger background worker autonomous loop
    background_tasks.add_task(execute_social_post, action_id, db)
    return {"status": "success", "message": f"Action {action_id} approved and sent to background worker."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
