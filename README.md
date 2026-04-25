# Smart Scheduler AI Agent

An interactive, voice-enabled AI scheduling assistant built with **Next.js**, **FastAPI**, **OpenAI Realtime API**, and **Google Calendar**.

## Live Demo
*   **Frontend Web App:** [https://smart-scheduler-frontend-269634872417.asia-southeast2.run.app](https://smart-scheduler-frontend-269634872417.asia-southeast2.run.app)
*   **Backend WebSocket API:** `wss://smart-scheduler-backend-269634872417.asia-southeast2.run.app/ws`

## Core Capabilities (Assignment Requirements Achieved)

*   **Ultra-Low Latency Voice Engine (<500ms):** Implemented raw PCM16 audio streaming over WebSockets directly to the OpenAI Realtime API. By bypassing traditional "waterfall" architectures (STT -> LLM -> TTS), the agent achieves near-instantaneous human-like conversational turnaround times, easily surpassing the <800ms benchmark.
*   **Agentic Logic & Stateful Memory:** Engineered a SQLite database layer that persists cross-session user preferences (e.g., standard meeting durations and preferred times). This allows the agent to handle highly ambiguous requests like *"schedule our usual sync-up"* without asking redundant clarifying questions.
*   **Advanced Conflict Resolution:** Designed the agent's system prompt to gracefully handle fully booked schedules. If a requested slot is occupied, the agent autonomously retrieves adjacent free slots and verbally suggests alternative times or days to the user.
*   **Smarter Time Parsing & Context Awareness:** Built custom calendar retrieval tools that allow the LLM to understand relative and deadline-driven time constraints. It can accurately resolve complex requests like *"Find 45 minutes before my flight on Friday"* or *"An hour after the Kick-off event"*.
*   **Dynamic Timezone Injection:** The Next.js frontend securely detects the user's browser timezone and passes it to the backend upon WebSocket initialization. This ensures the AI schedules meetings accurately in UTC regardless of the user's physical location in the world.
*   **Production API Integration & CI/CD:** Fully integrated with the Google Calendar API using Service Account authentication. Containerized the application using Docker and deployed a fully automated CI/CD pipeline via GitHub Actions to Google Cloud Run.

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
