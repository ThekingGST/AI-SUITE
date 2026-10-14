from __future__ import annotations

import random


SYSTEM_PROMPT = (
    "You are JARVIS, a calm, precise, futuristic desktop AI assistant. "
    "Be helpful, concise, and practical. When controlling the computer, explain only what matters."
)


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
