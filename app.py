from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import uuid
import time
import re

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# In-memory database for running/scheduled automations
automations = {}

# Initialize APScheduler for handling parallel background tasks
scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

class ChatMessage(BaseModel):
    message: str

# --- APSCHEDULER WORKER FUNCTION ---
def execute_automation(task_id: str):
    """Simulates a background automation process taking time and updating status logs."""
    if task_id not in automations:
        return
    
    automations[task_id]["status"] = "Processing HD Video..."
    time.sleep(5) # Simulating heavy work
    
    automations[task_id]["status"] = "Adding Metadata & Tags..."
    time.sleep(4)
    
    automations[task_id]["status"] = "Posted/Completed"

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Renders the main mobile layout."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat_endpoint(chat: ChatMessage):
    """Handles AI chat and task scheduling."""
    user_text = chat.message.lower()
    
    # Check if the user wants to schedule an automation
    if "schedule" in user_text:
        task_id = f"ID-{str(uuid.uuid4())[:4].upper()}"
        
        # Determine the execution method
        method = "Generic Task"
        if "instagram" in user_text: method = "Instagram Reel Upload"
        elif "youtube" in user_text: method = "YouTube Video Post"
        elif "drive" in user_text: method = "Google Drive Sync"
        
        # Look for a custom time (e.g., "5 am", "8:30 pm")
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', user_text)
        requested_time = time_match.group(1) if time_match else "Immediately"
        
        # Add to dashboard table
        automations[task_id] = {
            "id": task_id,
            "method": method,
            "status": f"Scheduled ({requested_time})"
        }
        
        # APScheduler: In a real app, we'd schedule this for the requested time.
        # For the sake of this live demo, we will trigger it 5 seconds from now 
        # so the user can watch the dashboard update live!
        run_date = datetime.now() + timedelta(seconds=5)
        scheduler.add_job(execute_automation, 'date', run_date=run_date, args=[task_id])
        
        ai_reply = f"Got it! I have scheduled the '{method}' automation for {requested_time}. (Demo mode: It will simulate execution in 5 seconds so you can watch the dashboard!)"
    
    else:
        ai_reply = "I'm your automation agent. Try saying: 'Schedule a YouTube video for 5 AM' or 'Schedule an Instagram post for 8 PM'."

    return JSONResponse(content={"reply": ai_reply})

@app.get("/api/automations")
async def get_automations():
    """Returns the live status of all tasks to populate the dashboard table."""
    # Convert dict to list for the frontend
    return JSONResponse(content={"automations": list(automations.values())})

@app.get("/oauth/{platform}", response_class=HTMLResponse)
async def mock_oauth(platform: str):
    """Mock OAuth route that acts as a simulated permission popup."""
    html_content = f"""
    <html>
        <body style="background:#121212; color:#fff; font-family:sans-serif; text-align:center; padding:50px;">
            <h2>{platform.capitalize()} Permission</h2>
            <p>Simulating secure OAuth handshake...</p>
            <script>
                setTimeout(() => {{
                    alert("{platform.capitalize()} Account Linked Successfully!");
                    window.close();
                }}, 1500);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
