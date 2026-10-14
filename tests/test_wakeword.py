import unittest
from jarvis_ai.voice.wakeword import WakeWordDetector

class TestWakeWord(unittest.TestCase):
    def setUp(self):
        self.detector = WakeWordDetector('jarvis')

    def test_english_wake_word(self):
        # Normal Vosk output
        self.assertTrue(self.detector.contains_wake_word('jarvis how are you'))
        self.assertEqual(self.detector.strip_wake_word('jarvis how are you'), 'how are you')
        
        # Whisper output with punctuation
        self.assertTrue(self.detector.contains_wake_word('Jarvis, how are you?'))
        self.assertEqual(self.detector.strip_wake_word('Jarvis, how are you?'), 'how are you')

    def test_hindi_wake_word(self):
        # Whisper Hindi output
        self.assertTrue(self.detector.contains_wake_word('जार्विस, मेरा नाम क्या है?'))
        self.assertEqual(self.detector.strip_wake_word('जार्विस, मेरा नाम क्या है?'), 'मेरा नाम क्या है')
        
        # Another alias (no punctuation)
        self.assertTrue(self.detector.contains_wake_word('जार्विस मेरा नाम क्या है'))
        self.assertEqual(self.detector.strip_wake_word('जार्विस मेरा नाम क्या है'), 'मेरा नाम क्या है')

    def test_telugu_wake_word(self):
        self.assertTrue(self.detector.contains_wake_word('జార్విస్, నా పేరు ఏమిటి?'))
        self.assertEqual(self.detector.strip_wake_word('జార్విస్, నా పేరు ఏమిటి?'), 'నా పేరు ఏమిటి')

    def test_no_wake_word(self):
        self.assertFalse(self.detector.contains_wake_word('how are you'))
        self.assertEqual(self.detector.strip_wake_word('how are you'), 'how are you')

if __name__ == '__main__':
    unittest.main()
