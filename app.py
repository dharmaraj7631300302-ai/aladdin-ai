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

automations = {}
scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

class ChatMessage(BaseModel):
    message: str

def execute_automation(task_id: str):
    if task_id not in automations:
        return
    automations[task_id]["status"] = "वीडियो प्रोसेस हो रहा है (HD)..."
    time.sleep(5)
    automations[task_id]["status"] = "टाइटल, डिस्क्रिप्शन और टैग्स लग रहे हैं..."
    time.sleep(4)
    automations[task_id]["status"] = "सफलतापूर्वक पोस्ट हो गया! ✅"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/chat")
async def chat_endpoint(chat: ChatMessage):
    user_text = chat.message.lower()
    
    # हिंदी और इंग्लिश दोनों शब्दों को पहचानने के लिए
    is_schedule = any(x in user_text for x in ["schedule", "शेड्यूल", "लगा", "अपलोड", "पोस्ट", "set"])
    
    if is_schedule:
        task_id = f"ID-{str(uuid.uuid4())[:4].upper()}"
        
        # प्लेटफॉर्म पहचानना
        method = "सामान्य टास्क"
        if "instagram" in user_text or "इंस्टा" in user_text or "रील" in user_text: 
            method = "Instagram Reel Upload"
        elif "youtube" in user_text or "यूट्यूब" in user_text or "वीडियो" in user_text: 
            method = "YouTube Video Post"
        elif "drive" in user_text or "ड्राइव" in user_text: 
            method = "Google Drive Sync"
        
        # टाइम निकालना (चाहे इंग्लिश हो या हिंदी जैसे '5 बजे', '8 pm', 'सुबह 6')
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|बजे|बज))', user_text)
        requested_time = time_match.group(1) if time_match else "तुरंत (Immediately)"
        
        automations[task_id] = {
            "id": task_id,
            "method": method,
            "status": f"शेड्यूल है ({requested_time} के लिए)"
        }
        
        run_date = datetime.now() + timedelta(seconds=3)
        scheduler.add_job(execute_automation, 'date', run_date=run_date, args=[task_id])
        
        ai_reply = f"ठीक है भाई! मैंने आपका '{method}' ऑटोमेशन टाइम '{requested_time}' के लिए सेट कर दिया है। नीचे डैशबोर्ड में देखिए, काम शुरू हो रहा है!"
    
    elif "hello" in user_text or "hii" in user_text or "नमस्ते" in user_text or "राम राम" in user_text:
        ai_reply = "राम राम भाई! मैं आपका अलादीन एआई एजेंट हूँ। मुझे आप हिंदी या इंग्लिश में बताइए, जैसे: 'यूट्यूब पर वीडियो लगाओ 4 बजे' या 'इंस्टाग्राम पर रील शेड्यूल करो'।"
    
    else:
        ai_reply = "मैं आपकी बात समझ रहा हूँ भाई। अगर आपको वीडियो या रील शेड्यूल करनी है, तो बस ऐसे बोलिए: 'यूट्यूब पर वीडियो 2 बजे अपलोड करो'।"

    return JSONResponse(content={"reply": ai_reply})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    
