from __future__ import annotations

import datetime
import random


def build_system_prompt() -> str:
    """Build the JARVIS system prompt with current date/time injected."""
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p").lstrip("0")

    return (
        "You are JARVIS, a calm, precise, and futuristic AI desktop assistant. "
        "You are inspired by the AI from Iron Man — intelligent, loyal, and efficient. "
        "You run locally on your owner's Windows PC.\n\n"
        f"Current date: {date_str}. Current time: {time_str}.\n\n"
        "YOUR REAL CAPABILITIES (describe these accurately when asked what you can do):\n"
        "- Voice recognition and natural text-to-speech\n"
        "- Real-time web search for current information, news, and factual queries\n"
        "- Face recognition and face detection via the webcam\n"
        "- Object detection via the webcam (YOLOv8)\n"
        "- Launch applications: Chrome, Calculator, Notepad, VS Code, Terminal, Paint, "
        "Task Manager, Explorer\n"
        "- Open websites: YouTube, Google, WhatsApp, Instagram\n"
        "- System control: adjust volume, adjust brightness, shutdown, restart, lock PC, "
        "take screenshots\n"
        "- File search and folder navigation on the local machine\n"
        "- Persistent memory: remember and recall user preferences\n"
        "- YouTube search and playback\n"
        "- Coding help, math, and general knowledge conversation\n\n"
        "CONVERSATION RULES:\n"
        "1. Be concise, natural, and conversational — never robotic or stiff.\n"
        "2. Understand follow-up messages using conversation history. "
        "If the user says 'tell me more', 'summarize it', 'explain that simply', "
        "'yes', 'go ahead', or uses pronouns like he/she/it/they/that/this, "
        "resolve them from what was discussed before.\n"
        "3. When asked for the current time or date, respond using the date and "
        "time shown above.\n"
        "4. When asked about your capabilities, list them accurately from the "
        "section above. Never invent capabilities you do not have.\n"
        "5. If you do not know something, say so honestly.\n"
        "6. Keep responses helpful and appropriately concise. Elaborate when asked.\n"
    )


# Backward-compatible constant — prefer build_system_prompt() for fresh date/time.
SYSTEM_PROMPT = build_system_prompt()


JOKES = (
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my CPU a joke. It processed it, but did not laugh.",
    "There are 10 kinds of people: those who understand binary and those who do not.",
)

QUOTES = (
    "Discipline turns ambition into architecture.",
    "Small improvements, repeated daily, become impossible to ignore.",
    "Focus is the quiet engine behind impressive work.",
)

FACTS = (
    "The first computer mouse was made of wood.",
    "A modern smartphone has more computing power than the computers used for Apollo guidance.",
    "The word robot comes from a Czech word meaning forced labor.",
)


def offline_reply(prompt: str) -> str:
    text = prompt.lower()
    if "joke" in text:
        return random.choice(JOKES)
    if "motivat" in text or "quote" in text:
        return random.choice(QUOTES)
    if "fact" in text:
        return random.choice(FACTS)
    if "who are you" in text:
        return "I am JARVIS, your local desktop assistant. My offline systems are active."
    return (
        "My local language model is not online yet, but I can still help with system commands, "
        "files, camera, memory, and automation. Start Ollama with llama3, mistral, or phi for richer answers."
    )
