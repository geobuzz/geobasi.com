#!/usr/bin/env python3
"""
Test Suite Completa per Sync Engine e Sincronizzazione Instagram:
1. Validazione formato shortcode (base64url).
2. Verifica coerenza shortcode <-> permalink.
3. Test d'integrazione di run_sync_all():
   - Esegue il flusso reale di run_sync_all() con dipendenze esterne simulate.
   - Simula il fallimento della scansione Instagram.
   - Verifica che catalogo e 4 post precedenti rimangano invariati.
   - Verifica che Instagram e pipeline risultino entrambi PARTIAL (e mai SUCCESS).
4. Test unitario sul calcolo dello stato globale della pipeline in presenza di ERROR, PARTIAL e SKIPPED.
"""
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Assicura import dei moduli dagli script
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import update_photos
import sync_engine

class TestInstagramValidation(unittest.TestCase):

    def test_shortcode_format_validation(self):
        """Verifica che la validazione distingua shortcode validi da stringhe non conformi."""
        valid_codes = [
            "De9uhu9jBpH",
            "DTYRRCOjN3Y",
            "DR2LhfdDIK1",
            "DLk6yC-s0pM",
            "DLkyyJjM79_",
            "ABC_123-xyz"
        ]
        for sc in valid_codes:
            self.assertTrue(
                update_photos.validate_shortcode_format(sc),
                f"Lo shortcode autentico '{sc}' dovrebbe risultare valido"
            )

        invalid_codes = [
            "",
            None,
            12345,
            "short",              # < 9 caratteri
            "A" * 25,             # > 15 caratteri
            "De9uhu9jBp!",        # '!' non consentito
            "De9uhu9jBp ",        # spazio non consentito
            "De9uhu9jBp$H",       # '$' non consentito
            "https://instagr.am"  # URL invece di shortcode
        ]
        for sc in invalid_codes:
            self.assertFalse(
                update_photos.validate_shortcode_format(sc),
                f"Lo shortcode '{sc}' dovrebbe risultare non valido"
            )

    def test_permalink_coherence(self):
        """Verifica la coerenza formale tra shortcode e permalink del post."""
        # Record coerente standard /p/
        valid_post_p = {
            "shortcode": "De9uhu9jBpH",
            "permalink": "https://www.instagram.com/p/De9uhu9jBpH/",
            "title": "Titolo test"
        }
        ok, reason = update_photos.validate_post_coherence(valid_post_p)
        self.assertTrue(ok, f"Dovrebbe essere valido ma ha restituito: {reason}")

        # Record coerente /reel/
        valid_post_reel = {
            "shortcode": "DLk6yC-s0pM",
            "permalink": "https://www.instagram.com/reel/DLk6yC-s0pM/",
            "title": "Titolo reel"
        }
        ok, reason = update_photos.validate_post_coherence(valid_post_reel)
        self.assertTrue(ok, f"Dovrebbe essere valido ma ha restituito: {reason}")

        # Record incoerente (shortcode diverso da quello nel permalink)
        incoherent_post = {
            "shortcode": "De9uhu9jBpH",
            "permalink": "https://www.instagram.com/p/ALTRACOSA123/",
            "title": "Titolo incoerente"
        }
        ok, reason = update_photos.validate_post_coherence(incoherent_post)
        self.assertFalse(ok)
        self.assertIn("Incoerenza tra shortcode", reason)

        # Permalink non Instagram
        external_post = {
            "shortcode": "De9uhu9jBpH",
            "permalink": "https://www.facebook.com/p/De9uhu9jBpH/",
            "title": "Titolo non instagram"
        }
        ok, reason = update_photos.validate_post_coherence(external_post)
        self.assertFalse(ok)
        self.assertIn("non conforme a Instagram", reason)


class TestPipelineStatusCalculation(unittest.TestCase):
    """Verifica il calcolo dello stato globale della pipeline in presenza di combinazioni ERROR, PARTIAL, SKIPPED."""

    def test_all_success(self):
        sources = {
            "substack": {"status": "SUCCESS", "count": 10},
            "instagram": {"status": "SUCCESS", "count": 4},
            "site_builder": {"status": "SUCCESS", "count": 1}
        }
        status, _ = sync_engine.compute_pipeline_status(sources, has_critical_error=False)
        self.assertEqual(status, "SUCCESS")

    def test_success_with_skipped(self):
        sources = {
            "substack": {"status": "SUCCESS", "count": 10},
            "linkedin_api": {"status": "SKIPPED", "count": 0},
            "instagram": {"status": "SUCCESS", "count": 4},
            "site_builder": {"status": "SUCCESS", "count": 1}
        }
        status, _ = sync_engine.compute_pipeline_status(sources, has_critical_error=False)
        self.assertEqual(status, "SUCCESS")

    def test_partial_status(self):
        sources = {
            "substack": {"status": "SUCCESS", "count": 10},
            "linkedin_api": {"status": "SKIPPED", "count": 0},
            "instagram": {"status": "PARTIAL", "count": 4},
            "site_builder": {"status": "SUCCESS", "count": 1}
        }
        status, _ = sync_engine.compute_pipeline_status(sources, has_critical_error=False)
        self.assertEqual(status, "PARTIAL")

    def test_error_status_takes_precedence_over_partial(self):
        sources = {
            "substack": {"status": "SUCCESS", "count": 10},
            "linkedin_api": {"status": "ERROR", "count": 0},
            "instagram": {"status": "PARTIAL", "count": 4},
            "site_builder": {"status": "SUCCESS", "count": 1}
        }
        status, _ = sync_engine.compute_pipeline_status(sources, has_critical_error=False)
        self.assertEqual(status, "ERROR")

    def test_has_critical_error_forces_error(self):
        sources = {
            "substack": {"status": "SUCCESS", "count": 10},
            "instagram": {"status": "SUCCESS", "count": 4}
        }
        status, _ = sync_engine.compute_pipeline_status(sources, has_critical_error=True)
        self.assertEqual(status, "ERROR")


class TestSyncEngineIntegration(unittest.TestCase):
    """
    Test d'integrazione che esegue il flusso reale di sync_engine.run_sync_all()
    con dipendenze esterne simulate.
    """

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "tmp_integration_data")
        os.makedirs(self.test_dir, exist_ok=True)
        
        self.catalog_file = os.path.join(self.test_dir, "instagram_catalog.json")
        self.photos_file = os.path.join(self.test_dir, "photos.json")
        self.log_file = os.path.join(self.test_dir, "sync_log.json")

        # Catalogo mock con 6 post validi
        self.initial_catalog = [
            {
                "shortcode": f"POST_{i:02d}_TEST",
                "permalink": f"https://www.instagram.com/p/POST_{i:02d}_TEST/",
                "title": f"Post mock n. {i}",
                "caption": f"Didascalia {i}",
                "date": "14 Nov 2026",
                "is_video": False,
                "likes": i * 10
            }
            for i in range(1, 7)
        ]
        with open(self.catalog_file, "w", encoding="utf-8") as f:
            json.dump(self.initial_catalog, f, indent=2)

        # 4 post precedenti selezionati
        self.initial_photos = self.initial_catalog[:4]
        with open(self.photos_file, "w", encoding="utf-8") as f:
            json.dump(self.initial_photos, f, indent=2)

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_run_sync_all_with_simulated_instagram_failure(self):
        """
        Esegue il flusso reale di sync_engine.run_sync_all():
        - Dipendenze esterne simulate (Substack mock, build mock, Instagram rate limit 429).
        - Verifica che catalogo e 4 post rimangano invariati.
        - Verifica che Instagram e pipeline risultino entrambi PARTIAL (e MAI SUCCESS).
        """
        with patch.object(sync_engine, "DATA_DIR", self.test_dir), \
             patch.object(sync_engine, "LOG_FILE", self.log_file), \
             patch.object(update_photos, "DATA_DIR", self.test_dir), \
             patch.object(update_photos, "CATALOG_FILE", self.catalog_file), \
             patch.object(update_photos, "PHOTOS_FILE", self.photos_file):

            # Snapshot prima dell'esecuzione
            with open(self.catalog_file, "r", encoding="utf-8") as f:
                catalog_before = f.read()
            with open(self.photos_file, "r", encoding="utf-8") as f:
                photos_before = f.read()

            # Mock delle dipendenze esterne:
            # 1. Substack restituisce articoli mock con successo
            # 2. Build mock eseguita con successo
            # 3. Instagram solleva errore di scansione (Rate Limit 429 / Login Wall)
            mock_articles = [{"title": "Articolo di test", "slug": "test-slug", "date": "14 Nov 2026"}]
            with patch("fetch_substack.fetch_articles", return_value=mock_articles), \
                 patch("build_site.build", return_value=True), \
                 patch("instaloader.Instaloader") as mock_instaloader:

                mock_instaloader.side_effect = ConnectionError("HTTP 429 Too Many Requests - Login Required")

                # Esecuzione del flusso REALE di run_sync_all()
                pipeline_status, sources_status = sync_engine.run_sync_all()

                # Verifica 1: Stato Instagram restituito e' PARTIAL e MAI SUCCESS
                ig_status = sources_status.get("instagram", {}).get("status")
                self.assertEqual(
                    ig_status, "PARTIAL",
                    f"Lo stato di Instagram nel Sync Engine deve essere PARTIAL, rilevato invece '{ig_status}'"
                )
                self.assertNotEqual(
                    ig_status, "SUCCESS",
                    "Lo stato di Instagram non deve MAI essere SUCCESS se la scansione live fallisce!"
                )

                # Verifica 2: Stato Pipeline globale e' PARTIAL e MAI SUCCESS
                self.assertEqual(
                    pipeline_status, "PARTIAL",
                    f"Lo stato globale della pipeline deve essere PARTIAL, rilevato invece '{pipeline_status}'"
                )
                self.assertNotEqual(
                    pipeline_status, "SUCCESS",
                    "Lo stato globale della pipeline non deve MAI essere SUCCESS se una fonte e' PARTIAL!"
                )

                # Verifica 3: instagram_catalog.json e' rimasto rigorosamente invariato
                with open(self.catalog_file, "r", encoding="utf-8") as f:
                    catalog_after = f.read()
                self.assertEqual(
                    catalog_before, catalog_after,
                    "CRITICO: instagram_catalog.json e' stato modificato nonostante il fallimento della scansione!"
                )

                # Verifica 4: i 4 post precedenti in photos.json sono stati mantenuti invariati
                with open(self.photos_file, "r", encoding="utf-8") as f:
                    photos_after = f.read()
                self.assertEqual(
                    photos_before, photos_after,
                    "CRITICO: I 4 post precedenti in photos.json sono stati modificati invece di essere mantenuti!"
                )

                # Verifica 5: Controllo del file di persistenza sync_log.json
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)

                logged_ig = [l for l in logs if l.get("source") == "instagram"]
                logged_pipeline = [l for l in logs if l.get("source") == "pipeline"]

                self.assertTrue(len(logged_ig) > 0, "Manca la voce instagram in sync_log.json")
                self.assertTrue(len(logged_pipeline) > 0, "Manca la voce pipeline in sync_log.json")

                self.assertEqual(logged_ig[0]["status"], "PARTIAL")
                self.assertNotEqual(logged_ig[0]["status"], "SUCCESS")

                self.assertEqual(logged_pipeline[0]["status"], "PARTIAL")
                self.assertNotEqual(logged_pipeline[0]["status"], "SUCCESS")

if __name__ == "__main__":
    unittest.main()
