"""Fictional local demo; memory is reset on restart. Run with one worker only."""

from datetime import datetime, timezone
import re
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator


class RegistrationInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)

    @field_validator("name", "email", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value.casefold()


def seed_events() -> list[dict]:
    return [
        {
            "id": "e1", "title": "周末陶艺工作坊", "category": "手作",
            "date": "2026-10-17", "time": "14:00", "location": "纸飞机空间 · A 室",
            "capacity": 8, "description": "用一小块陶土，做一只属于自己的杯子。零基础也可以参加。",
            "accent": "orange",
        },
        {
            "id": "e2", "title": "设计灵感交换会", "category": "分享",
            "date": "2026-10-18", "time": "10:30", "location": "纸飞机空间 · B 室",
            "capacity": 6, "description": "带来一个最近喜欢的设计，和新朋友聊聊它背后的想法。",
            "accent": "green",
        },
        {
            "id": "e3", "title": "一对一手冲咖啡体验", "category": "体验",
            "date": "2026-10-18", "time": "15:00", "location": "纸飞机空间 · 咖啡角",
            "capacity": 1, "description": "从磨豆到注水，体验一杯手冲咖啡的制作过程。",
            "accent": "purple",
        },
    ]


def seed_registrations() -> list[dict]:
    guests = [("e1", "小橙"), ("e1", "薄荷"), ("e1", "云朵"),
              ("e2", "青禾"), ("e2", "木棉"), ("e3", "小满")]
    return [
        {
            "id": f"r{index}", "eventId": event_id, "name": name,
            "email": f"guest{index}@example.test", "status": "active",
            "createdAt": "2026-09-15T09:00:00+00:00",
        }
        for index, (event_id, name) in enumerate(guests, start=1)
    ]


class MemoryStore:
    def __init__(self) -> None:
        self.lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.events = seed_events()
            self.registrations = seed_registrations()

    def event(self, event_id: str) -> dict:
        # Callers hold the store lock for the complete read or write operation.
        event = next((item for item in self.events if item["id"] == event_id), None)
        if event is None:
            raise HTTPException(404, "Event not found")
        return event

    def active_registrations(self, event_id: str) -> list[dict]:
        return [item for item in self.registrations
                if item["eventId"] == event_id and item["status"] == "active"]


store = MemoryStore()
app = FastAPI(title="Gather Workshop Demo", version="0.1.0")


@app.middleware("http")
async def demo_failure(request: Request, call_next):
    writing = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    failure = request.headers.get("X-Demo-Fail")
    if writing and failure == "1":
        return JSONResponse(status_code=503, content={"detail": "Simulated service failure. Please try again."})
    response = await call_next(request)
    if writing and failure == "after" and 200 <= response.status_code < 300:
        return JSONResponse(status_code=503, content={
            "detail": "Simulated lost response: the write may have succeeded. Verify before retrying."
        })
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5177", "http://127.0.0.1:5177"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Demo-Fail"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "mode": "local-memory-demo"}


@app.get("/api/events")
def list_events() -> dict:
    with store.lock:
        return {"items": [
            {**event, "activeCount": len(store.active_registrations(event["id"]))}
            for event in store.events
        ]}


@app.get("/api/events/{event_id}/registrations")
def list_registrations(event_id: str) -> dict:
    with store.lock:
        store.event(event_id)
        return {"items": [dict(item) for item in store.registrations if item["eventId"] == event_id]}


@app.post("/api/events/{event_id}/registrations", status_code=201)
def create_registration(event_id: str, payload: RegistrationInput) -> dict:
    with store.lock:
        event = store.event(event_id)
        active = store.active_registrations(event_id)
        if any(item["email"].casefold() == payload.email for item in active):
            raise HTTPException(409, "This email is already registered for this event")
        if len(active) >= event["capacity"]:
            raise HTTPException(409, "This event is full")
        registration = {
            "id": f"r-{uuid4().hex}", "eventId": event_id,
            "name": payload.name, "email": payload.email, "status": "active",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        store.registrations.append(registration)
        return dict(registration)


@app.post("/api/demo/reset")
def reset_demo() -> dict:
    store.reset()
    return {"ok": True}
