import unittest

from scripts.ingest_docs import extract_legal_metadata


class TestMetadataExtraction(unittest.TestCase):
    def test_examples(self):
        cases = [
            (
                "AGU (LC 73 de 1993).docx",
                {"type": "Lei Complementar", "number": "73", "year": 1993, "authority": "AGU"},
            ),
            ("Súmulas STF atualizado.docx", {"type": "Súmula", "authority": "STF"}),
            ("Lei 8666.docx", {"type": "Lei", "number": "8666"}),
            ("Decreto 10024.docx", {"type": "Decreto", "number": "10024"}),
            (
                "Portaria Normativa AGU n. 46, de 2022.docx",
                {"type": "Portaria", "number": "46", "year": 2022, "authority": "AGU"},
            ),
            (
                "sumulas do TJRJ-2023.pdf",
                {"type": "Súmula", "year": 2023, "authority": "TJRJ"},
            ),
            ("Estatuto da Cidade (Lei 10257).docx", {"type": "Lei", "number": "10257"}),
            ("LC_73.pdf", {"type": "Lei Complementar", "number": "73"}),
        ]

        # 1. Positive Test Cases
        for filename, expected in cases:
            with self.subTest(filename=filename):
                result = extract_legal_metadata(filename)

                # Robust assertions
                self.assertIsNotNone(result, f"Result should not be None for {filename}")
                self.assertIsInstance(result, dict, f"Result should be a dict for {filename}")

                for k, v in expected.items():
                    self.assertEqual(
                        result.get(k),
                        v,
                        f"Failed for {filename}: expected {k}={v}, got {result.get(k)}",
                    )

    def test_negative_cases(self):
        """Ensure invalid inputs don't crash and return safe defaults."""
        cases = [
            ("", {}),
            ("arquivo_sem_nada.txt", {}),
            ("receitas_de_bolo.docx", {}),
            ("123456.pdf", {}),  # Just numbers, no context
        ]

        for filename, expected in cases:
            with self.subTest(filename=filename):
                result = extract_legal_metadata(filename)
                self.assertIsInstance(result, dict)
                # Ensure main legal keys are NOT present or empty logic holds
                self.assertEqual(result, expected, f"Failed negative case: {filename}")


if __name__ == "__main__":
    unittest.main()
