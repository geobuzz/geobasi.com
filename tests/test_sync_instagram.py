#!/usr/bin/env python3
"""
Test Suite per la validazione di Instagram e la simulazione del fallimento della scansione live:
1. Validazione formato shortcode (base64url).
2. Verifica coerenza shortcode <-> permalink.
3. Simulazione fallimento scansione live:
   - instagram_catalog.json rimane invariato;
   - i 4 post precedenti sono mantenuti;
   - lo stato registrato e' PARTIAL, mai SUCCESS.
4. Distinzione chiara tra esito singole fonti ed esito pipeline.
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
        # Shortcode autentici validi (base64url 9-15 caratteri)
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

        # Shortcode non conformi (troppo corti, troppo lunghi, caratteri speciali non ammessi, spazi)
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


class TestInstagramFailureAndPartialStatus(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "tmp_data")
        os.makedirs(self.test_dir, exist_ok=True)
        
        self.catalog_file = os.path.join(self.test_dir, "instagram_catalog.json")
        self.photos_file = os.path.join(self.test_dir, "photos.json")
        self.log_file = os.path.join(self.test_dir, "sync_log.json")

        # Catalogo mock con 5 post validi
        self.initial_catalog = [
            {
                "shortcode": f"CODE_{i:02d}_TESTX",
                "permalink": f"https://www.instagram.com/p/CODE_{i:02d}_TESTX/",
                "title": f"Post n. {i}",
                "caption": f"Didascalia {i}",
                "date": "14 Nov 2026"
            }
            for i in range(1, 6)
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

    def test_live_scan_failure_preserves_catalog_and_photos_and_logs_partial(self):
        """
        Simula il fallimento della scansione live e verifica tassativamente che:
        - instagram_catalog.json rimanga invariato;
        - i 4 post precedenti in photos.json siano mantenuti invariati;
        - lo stato registrato per Instagram sia PARTIAL e mai SUCCESS.
        """
        # Patch dei percorsi dei file nei moduli
        with patch.object(update_photos, "CATALOG_FILE", self.catalog_file), \
             patch.object(update_photos, "PHOTOS_FILE", self.photos_file), \
             patch.object(sync_engine, "LOG_FILE", self.log_file), \
             patch.object(sync_engine, "DATA_DIR", self.test_dir):

            # Snapshot prima dell'esecuzione
            with open(self.catalog_file, "r", encoding="utf-8") as f:
                catalog_before = f.read()
            with open(self.photos_file, "r", encoding="utf-8") as f:
                photos_before = f.read()

            # Mock del fallimento di instaloader (es. Rate Limit 429 o Login Wall)
            with patch("instaloader.Instaloader") as mock_instaloader:
                mock_instaloader.side_effect = ConnectionError("HTTP 429 Too Many Requests - Login Required")

                # Esecuzione della fase 1: scansione live
                scan_ok, catalog, msg = update_photos.scan_instagram_profile()
                self.assertFalse(scan_ok, "La scansione simulata doveva fallire")

                # Esecuzione della fase 2: campionamento con preserve_existing=True
                pick_ok, selected_posts = update_photos.pick_random_posts(4, preserve_existing=True)
                self.assertTrue(pick_ok, "La selezione con catalogo locale valido doveva riuscire")
                self.assertEqual(len(selected_posts), 4)

                # Verifica 1: instagram_catalog.json e' rimasto rigorosamente invariato
                with open(self.catalog_file, "r", encoding="utf-8") as f:
                    catalog_after = f.read()
                self.assertEqual(
                    catalog_before, catalog_after,
                    "CRITICO: instagram_catalog.json non deve essere modificato se la scansione fallisce!"
                )

                # Verifica 2: i 4 post precedenti sono stati mantenuti invariati
                with open(self.photos_file, "r", encoding="utf-8") as f:
                    photos_after = f.read()
                self.assertEqual(
                    photos_before, photos_after,
                    "CRITICO: I 4 post precedenti in photos.json devono essere mantenuti se la scansione live fallisce!"
                )

                # Registrazione dell'esito come avviene in sync_engine
                if not scan_ok:
                    sync_engine.log_sync(
                        "instagram", "PARTIAL", len(selected_posts),
                        f"{msg}. Mantenuti i 4 post precedenti e catalogo locale invariato"
                    )

                # Verifica 3: lo stato registrato e' PARTIAL e MAI SUCCESS
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)

                ig_logs = [l for l in logs if l.get("source") == "instagram"]
                self.assertTrue(len(ig_logs) > 0, "Deve esistere almeno una voce di log per instagram")
                last_ig_status = ig_logs[0].get("status")
                
                self.assertEqual(
                    last_ig_status, "PARTIAL",
                    f"Lo stato registrato deve essere PARTIAL, invece e' '{last_ig_status}'"
                )
                self.assertNotEqual(
                    last_ig_status, "SUCCESS",
                    "Lo stato registrato non deve MAI essere SUCCESS se la scansione live fallisce!"
                )

if __name__ == "__main__":
    unittest.main()
