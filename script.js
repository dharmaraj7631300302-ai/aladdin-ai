// ==========================================
// CONFIGURATION
// ==========================================
// Change this to your Render backend URL once deployed.
const BACKEND_URL = "http://localhost:8000"; 
const USER_ID = "user_123"; // Stub user ID. In prod, fetch from JWT.

// DOM Elements
const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const avatar = document.getElementById('avatar');
const pendingActionsContainer = document.getElementById('pending-actions');

// ==========================================
// 1. WEB AUDIO API (STT & TTS)
// ==========================================
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = SpeechRecognition ? new SpeechRecognition() : null;

if (recognition) {
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        micBtn.classList.add('listening', 'bg-green-600');
        chatInput.placeholder = "Listening...";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        sendMessage(); // Auto-send voice input
    };

    recognition.onend = () => {
        micBtn.classList.remove('listening', 'bg-green-600');
        chatInput.placeholder = "Type or speak commands...";
    };

    micBtn.addEventListener('click', () => {
        try { recognition.start(); } catch (e) { console.warn("Mic already active"); }
    });
} else {
    micBtn.style.display = 'none';
    console.warn("Speech Recognition API not supported in this browser.");
}

function speakText(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.1;
        
        // Simple avatar lip-sync animation simulation
        utterance.onstart = () => avatar.style.transform = "scale(1.1)";
        utterance.onend = () => avatar.style.transform = "scale(1)";
        
        window.speechSynthesis.speak(utterance);
    }
}

// ==========================================
// 2. CHAT & AGENTIC API COMMUNICATION
// ==========================================
function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `p-3 rounded-lg max-w-[80%] ${sender === 'user' ? 'bg-blue-600 ml-auto' : 'bg-gray-700 mr-auto'}`;
    msgDiv.innerText = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    appendMessage('user', msg);
    chatInput.value = '';

    try {
        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID, message: msg })
        });
        const data = await response.json();
        
        appendMessage('ai', data.reply);
        speakText(data.reply);
        
        // Auto-refresh the HITL queue if the AI staged an action
        if(data.reply.includes("queue") || data.reply.includes("waiting")) {
            setTimeout(fetchPendingActions, 1000);
        }

    } catch (error) {
        console.error("Error communicating with AI:", error);
        appendMessage('ai', "⚠️ Network error connecting to backend logic.");
    }
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// ==========================================
// 3. HUMAN-IN-THE-LOOP (HITL) APPROVAL SYSTEM
// ==========================================
async function fetchPendingActions() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/actions/pending`);
        const actions = await response.json();
        
        pendingActionsContainer.innerHTML = ''; // Clear

        if (actions.length === 0) {
            pendingActionsContainer.innerHTML = '<div class="text-sm text-gray-400 text-center">No pending actions.</div>';
            return;
        }

        actions.forEach(action => {
            const card = document.createElement('div');
            card.className = "bg-gray-700 p-3 rounded-md shadow-md border-l-4 border-yellow-500";
            card.innerHTML = `
                <div class="text-sm font-bold text-yellow-400">Pending: ${action.type.replace('_', ' ').toUpperCase()}</div>
                <div class="text-xs text-gray-300 mt-1 mb-2 font-mono">${action.payload}</div>
                <button onclick="approveAction(${action.id}, this)" class="w-full bg-green-600 hover:bg-green-500 text-white py-1 rounded text-sm transition">
                    Approve Task
                </button>
            `;
            pendingActionsContainer.appendChild(card);
        });

    } catch (error) {
        console.error("Failed to fetch queue", error);
    }
}

async function approveAction(id, buttonElement) {
    buttonElement.innerText = "Approving...";
    buttonElement.disabled = true;
    buttonElement.classList.replace('bg-green-600', 'bg-gray-500');

    try {
        const response = await fetch(`${BACKEND_URL}/api/actions/${id}/approve`, { method: 'POST' });
        const result = await response.json();
        if (result.status === "success") {
            appendMessage('ai', `System Update: Task #${id} approved. Executing autonomous background process...`);
            setTimeout(fetchPendingActions, 500); // refresh queue
        }
    } catch (error) {
        buttonElement.innerText = "Error!";
        console.error("Failed to approve action", error);
    }
}

// Initial fetch of pending items
fetchPendingActions();
