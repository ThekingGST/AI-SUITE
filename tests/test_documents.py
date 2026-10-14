import os
import unittest
from pathlib import Path
import json

from shared.documents.parsers import ParserRegistry
from shared.documents.context import DocumentStore, Retriever
from shared.documents.generators import GeneratorManager

class TestDocumentIntelligence(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = Path("tests/test_files")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.store = DocumentStore()
        
    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            
    def _make_file(self, name, content):
        p = self.test_dir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_text_and_markdown(self):
        txt = self._make_file("test.txt", "Hello\n\nWorld")
        md = self._make_file("test.md", "# Title\n\nBody")
        
        doc_txt = self.store.attach_file(txt)
        doc_md = self.store.attach_file(md)
        
        self.assertEqual(len(doc_txt.chunks), 2)
        self.assertEqual(len(doc_md.chunks), 2)

    def test_json_parsing(self):
        js = self._make_file("test.json", json.dumps({"key": "value"}))
        doc = self.store.attach_file(js)
        self.assertIn("value", doc.full_text)

    def test_corrupt_file_graceful(self):
        # Even if a file is just garbage, TextParser will try to read it as text.
        # But let's test a fake PDF
        fake_pdf = self.test_dir / "fake.pdf"
        fake_pdf.write_bytes(b"Not a real PDF")
        
        doc = self.store.attach_file(fake_pdf)
        self.assertTrue(getattr(doc, 'failed', False))
            
    def test_retrieval(self):
        txt = self._make_file("ret.txt", "The quick brown fox jumps over the lazy dog.")
        self.store.attach_file(txt)
        
        retriever = Retriever(self.store)
        context = retriever.retrieve("fox dog")
        self.assertIn("quick brown", context)
        
        # Test empty query
        empty_ctx = retriever.retrieve("")
        self.assertIn("ATTACHED_DOCUMENTS", empty_ctx)

    def test_removal(self):
        txt = self._make_file("rem.txt", "Remove me")
        doc = self.store.attach_file(txt)
        self.assertTrue(doc.doc_id in self.store.documents)
        self.store.remove_file(doc.doc_id)
        self.assertFalse(doc.doc_id in self.store.documents)

    def test_generators(self):
        gen = GeneratorManager()
        
        # We need a custom dir for tests to avoid polluting user Documents
        gen._get_safe_output_dir = lambda: self.test_dir
        
        # Test TXT
        p_txt = gen.generate_file("Text content", "out", ".txt")
        self.assertTrue(p_txt.exists())
        self.assertEqual(p_txt.read_text(encoding="utf-8"), "Text content")
        
        # Test CSV
        p_csv = gen.generate_file("col1,col2\\n1,2", "out", ".csv")
        self.assertTrue(p_csv.exists())
        
        # Test XLSX
        p_xlsx = gen.generate_file("col1,col2\\n1,2", "out", ".xlsx")
        self.assertTrue(p_xlsx.exists())
        
        # Test collision handling
        p_txt2 = gen.generate_file("Text content", "out", ".txt")
        self.assertEqual(p_txt2.name, "out_1.txt")
        
    def test_path_traversal_prevention(self):
        gen = GeneratorManager()
        gen._get_safe_output_dir = lambda: self.test_dir
        
        p = gen.generate_file("Hack", "../../../../evil", ".txt")
        self.assertEqual(p.parent, self.test_dir)
        self.assertIn("evil", p.name)
        self.assertNotIn("..", p.name)


    def test_retrieval_content(self):
        # Create a mock PDF
        path = self.test_dir / "test_knowledge.pdf"
        import reportlab.pdfgen.canvas
        c = reportlab.pdfgen.canvas.Canvas(str(path))
        c.drawString(100, 750, "The secret passcode is 987654.")
        c.drawString(100, 730, "The main topic is DWDM.")
        c.save()

        # Attach
        doc = self.store.attach_file(path)
        
        # Query
        retriever = Retriever(self.store)
        
        res1 = retriever.retrieve("summarize this pdf")
        self.assertIn("987654", res1)
        
        res2 = retriever.retrieve("what is the secret passcode?")
        self.assertIn("987654", res2)
        
        res3 = retriever.retrieve("what is in this ppt")
        self.assertIn("DWDM", res3)
        
if __name__ == "__main__":
    unittest.main()
