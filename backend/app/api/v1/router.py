from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    companies,
    conversations,
    documents,
    events,
    expenses,
    ideas,
    people,
    preferences,
    projects,
    reminders,
    tags,
    tasks,
    voice,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(voice.router)
api_router.include_router(people.router)
api_router.include_router(companies.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(events.router)
api_router.include_router(reminders.router)
api_router.include_router(ideas.router)
api_router.include_router(expenses.router)
api_router.include_router(documents.router)
api_router.include_router(tags.router)
api_router.include_router(preferences.router)
