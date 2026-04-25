import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from services.calendar import check_calendar_availability, schedule_meeting, find_reference_event, get_current_time
from database import SessionLocal
import models

from dotenv import load_dotenv

# Load environments appropriately
env_file = ".env.production" if os.environ.get("APP_ENV") == "production" else ".env.development"
load_dotenv(env_file)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"

SYSTEM_PROMPT = """You are a highly capable AI scheduling assistant named the 'Smart Scheduler'.
Your goal is to help users find and schedule meeting times through a natural conversation.

Capabilities & Rules:
1. Always maintain context of the meeting duration and preferences.
2. If a user asks for a vague time (e.g., 'sometime next week'), propose 2-3 specific times.
3. If the user asks for a time relative to another event (e.g., 'after my flight'), call `find_reference_event` to locate it, then search for availability.
4. If the requested time is fully booked, DO NOT just say it's booked. Always autonomously call `check_calendar_availability` for adjacent times (earlier, later, or the next day) and propose those alternatives immediately. 
5. The current time is available via `get_current_time`. Use it to understand 'today', 'tomorrow', etc. Pay close attention to the timezone offset returned by this tool and schedule all events in that local timezone.

Keep your spoken responses natural, concise, and conversational. Do not read out raw data or IDs.
"""

TOOLS = [
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Returns the current UTC time. Call this to orient yourself when the user says 'today', 'tomorrow', etc.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "check_calendar_availability",
        "description": "Checks the calendar for free/busy times in a given window.",
        "parameters": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "ISO 8601 string for start time"},
                "time_max": {"type": "string", "description": "ISO 8601 string for end time"}
            },
            "required": ["time_min", "time_max"]
        }
    },
    {
        "type": "function",
        "name": "schedule_meeting",
        "description": "Schedules a meeting on the calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Title of the meeting"},
                "start_time": {"type": "string", "description": "ISO 8601 start time"},
                "end_time": {"type": "string", "description": "ISO 8601 end time"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "type": "function",
        "name": "find_reference_event",
        "description": "Searches for an event on the calendar by a query string (e.g. 'flight', 'kick-off').",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search term"}
            },
            "required": ["query"]
        }
    }
]

async def handle_tool_call(call_id, name, arguments_str):
    try:
        args = json.loads(arguments_str)
        result = {}
        if name == "get_current_time":
            result = {"current_time": get_current_time()}
        elif name == "check_calendar_availability":
            result = check_calendar_availability(args['time_min'], args['time_max'])
        elif name == "schedule_meeting":
            result = schedule_meeting(args['summary'], args['start_time'], args['end_time'])
        elif name == "find_reference_event":
            result = find_reference_event(args['query'])
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result)
            }
        }
    except Exception as e:
        print(f"Tool call error: {e}")
        return {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps({"error": str(e)})
            }
        }

async def openai_realtime_bridge(client_websocket):
    """
    Bridges the Next.js frontend WebSocket with the OpenAI Realtime API.
    """
    if not OPENAI_API_KEY:
        await client_websocket.send_text(json.dumps({"type": "error", "message": "OPENAI_API_KEY is not set"}))
        return

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        # Fetch user preferences
        db = SessionLocal()
        user_pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == "default_user").first()
        if not user_pref:
            # Create default if not exists
            user_pref = models.UserPreference(
                user_id="default_user",
                standard_meeting_duration=30,
                preferred_time_of_day="Any",
                memory_context="User is a busy founder."
            )
            db.add(user_pref)
            db.commit()
            db.refresh(user_pref)
        
        user_context_prompt = f"\n\nUser Preferences Context:\n- Standard meeting duration: {user_pref.standard_meeting_duration} minutes.\n- Preferred time of day: {user_pref.preferred_time_of_day}.\n- Additional context: {user_pref.memory_context}\nUse this context when the user refers to their 'usual' meeting or 'normal' preferences."
        db.close()

        async with websockets.connect(URL, additional_headers=headers) as openai_ws:
            print("Connected to OpenAI Realtime")
            
            # Initialize session
            init_event = {
                "type": "session.update",
                "session": {
                    "instructions": SYSTEM_PROMPT + user_context_prompt,
                    "voice": "alloy",
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "turn_detection": None
                }
            }
            await openai_ws.send(json.dumps(init_event))

            # Task to receive from Frontend and send to OpenAI
            async def receive_from_client(): 
                try:
                    while True:
                        message = await client_websocket.receive_text()
                        # Pass through JSON commands or audio directly
                        await openai_ws.send(message)
                except Exception as e:
                    print(f"Client disconnected: {e}")

            # Task to receive from OpenAI and send to Frontend
            async def receive_from_openai():
                try:
                    while True:
                        response = await openai_ws.recv()
                        event = json.loads(response)
                        
                        # Forward to client so frontend can play audio
                        await client_websocket.send_text(response)

                        # Intercept tool calls to execute them on the backend
                        if event.get("type") == "response.function_call_arguments.done":
                            call_id = event.get("call_id")
                            name = event.get("name")
                            arguments = event.get("arguments")
                            print(f"Executing tool: {name}")
                            
                            # Execute the tool
                            tool_output_event = await handle_tool_call(call_id, name, arguments)
                            
                            if name == "schedule_meeting":
                                try:
                                    meeting_details = json.loads(tool_output_event["item"]["output"])
                                    if meeting_details.get("status") == "success":
                                        args_dict = json.loads(arguments)
                                        meeting_data = {
                                            "type": "meeting_scheduled",
                                            "summary": args_dict.get("summary", "Meeting"),
                                            "start": args_dict.get("start_time"),
                                            "end": args_dict.get("end_time"),
                                            "link": meeting_details.get("eventLink")
                                        }
                                        await client_websocket.send_text(json.dumps(meeting_data))
                                except Exception as e:
                                    print(f"Failed to forward meeting: {e}")
                            
                            # Send the result back to OpenAI
                            await openai_ws.send(json.dumps(tool_output_event))
                            
                            # Prompt OpenAI to create a response based on the tool output
                            await openai_ws.send(json.dumps({"type": "response.create"}))

                except Exception as e:
                    print(f"OpenAI disconnected: {e}")

            await asyncio.gather(
                receive_from_client(),
                receive_from_openai()
            )

    except Exception as e:
        print(f"Failed to connect to OpenAI: {e}")
        await client_websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
