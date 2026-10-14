import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty('voices')

for v in voices:
    print(v.id)

engine.setProperty('rate', 170)
engine.setProperty('volume', 1.0)

engine.say("Systems online.")
engine.runAndWait()