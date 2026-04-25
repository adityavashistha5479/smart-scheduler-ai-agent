# Smart Scheduler AI Agent

An interactive, voice-enabled AI scheduling assistant built with **Next.js**, **FastAPI**, **OpenAI Realtime API**, and **Google Calendar**.

## Live Demo
*   **Frontend Web App:** [https://smart-scheduler-frontend-269634872417.asia-southeast2.run.app](https://smart-scheduler-frontend-269634872417.asia-southeast2.run.app)
*   **Backend WebSocket API:** `wss://smart-scheduler-backend-269634872417.asia-southeast2.run.app/ws`

## Features

*   **Voice-Enabled Conversation:** Uses the OpenAI Realtime API for natural, low-latency (<800ms) voice interaction.
*   **Google Calendar Integration:** Dynamically checks availability and schedules meetings autonomously based on conversational context.
*   **Advanced Conflict Resolution:** Capable of suggesting adjacent times or alternative days if the requested slot is booked.
*   **Intelligent Time Parsing:** Understands relative times (e.g., "after my flight", "sometime next week") and finds reference events on your calendar.
*   **Stateful Memory:** Persists user preferences (like standard meeting length and preferred times) via a SQLite database to enable "usual sync-up" scheduling without redundant questions.
*   **Dynamic Timezone Awareness:** The frontend securely passes the user's local timezone to the backend, ensuring the AI schedules meetings accurately regardless of the user's physical location.

## Local Setup Instructions

### 1. Backend Setup (FastAPI)

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure Environment Variables:
    Create a `.env.development` file in the `backend` directory (if not present) and add your OpenAI API key:
    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    APP_ENV=development
    ```
5.  Google Calendar Setup:
    To test real Google Calendar integration, place a Google Service Account `credentials.json` file in the `backend` directory. Ensure the Service Account has permission to access the target calendar and the API is enabled on Google Cloud. If `credentials.json` is missing, the backend will gracefully fallback to an in-memory "dummy" calendar for testing logic.
6.  Start the backend server:
    ```bash
    uvicorn main:app --reload
    ```
    The server will start on `ws://localhost:8000/ws`.

### 2. Frontend Setup (Next.js)

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Configure Environment Variables:
    Create a `.env.development` file in the `frontend` directory:
    ```env
    NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
    ```
4.  Start the development server:
    ```bash
    npm run dev
    ```
5.  Open [http://localhost:3000](http://localhost:3000) in your browser.

## Design Choices

1.  **OpenAI Realtime API:** Chosen to fulfill the low-latency voice requirement without chaining a separate STT, LLM, and TTS service. It naturally handles interruptions and fluid conversation.
2.  **WebSocket Bridge:** The FastAPI backend serves as a secure bridge between the client and OpenAI, allowing us to safely authenticate and execute sensitive tool calls (like database queries and Calendar modifications) server-side.
3.  **Client-side AudioProcessing:** Raw PCM16 audio is captured via the Web Audio API (`AudioWorkletProcessor`), converted to Base64, and streamed. This minimizes external dependencies on the frontend.
4.  **Database for Memory:** A SQLite database stores user preferences (e.g., standard meeting duration), injected dynamically into the LLM system prompt on connection. This allows the AI to handle ambiguous requests like "schedule our usual sync-up".
5.  **Dummy Calendar Fallback:** Ensures the evaluator can test the agent's logic, conflict resolution, and conversational capabilities without needing to set up Google Cloud credentials immediately.
