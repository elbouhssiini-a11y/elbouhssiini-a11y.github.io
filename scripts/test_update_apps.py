#!/usr/bin/env python3
"""Security and catalog tests for the App Store Connect updater."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("update_apps", ROOT / "scripts" / "update_apps.py")
update_apps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update_apps)


def pem_key():
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")


class CatalogTests(unittest.TestCase):
    def test_token_does_not_contain_the_private_key(self):
        private_key = pem_key()
        token = update_apps.make_token("KEY123", "ISSUER-UUID", private_key)
        self.assertNotIn("PRIVATE KEY", token)
        self.assertNotIn(private_key, token)

    def test_missing_credentials_do_not_echo_values(self):
        with mock.patch.dict("os.environ", {"APP_STORE_CONNECT_PRIVATE_KEY": "super-secret-value"}, clear=True):
            with self.assertRaises(update_apps.CatalogError) as caught:
                update_apps.require_credentials()
        self.assertNotIn("super-secret-value", str(caught.exception))
        self.assertIn("APP_STORE_CONNECT_KEY_ID", str(caught.exception))

    def test_known_copy_is_kept_and_new_app_is_discovered(self):
        copies = {
            "6783467232": {
                "name": "SillySmile Live 4K Walls",
                "description": "An iOS wallpaper experience built for discovering and enjoying high-quality 4K and live wallpapers, with a polished native experience.",
                "icon": "assets/icons/sillysmile.png",
                "url": "https://apps.apple.com/ma/app/sillysmile-live-4k-walls/id6783467232",
                "featured": True,
            }
        }
        apps = {
            "data": [
                {"id": "6783467232", "attributes": {"name": "SillySmile Live 4K Walls", "primaryLocale": "en-US"}},
                {"id": "111111111", "attributes": {"name": "Draft Only", "primaryLocale": "en-US"}},
                {"id": "222222222", "attributes": {"name": "Northline", "primaryLocale": "en-US"}},
            ]
        }

        def asc(path, params):
            if path == "/v1/apps":
                return apps
            if path.endswith("/appStoreVersions"):
                app_id = path.split("/")[3]
                if app_id == "111111111":
                    return {"data": []}
                return {"data": [{"id": "ver-" + app_id, "attributes": {"appStoreState": "READY_FOR_SALE"}}]}
            if "/appStoreVersionLocalizations" in path:
                if "222222222" in path:
                    return {
                        "data": [
                            {
                                "attributes": {
                                    "locale": "en-US",
                                    "promotionalText": "A quiet notes app for iPhone.",
                                    "description": "Longer store text that must not replace the short promotional text.",
                                }
                            }
                        ]
                    }
                return {"data": [{"attributes": {"locale": "en-US", "description": "Store description."}}]}
            if path.endswith("/appInfos"):
                return {"data": [{"id": "info", "attributes": {"appStoreState": "READY_FOR_DISTRIBUTION"}}]}
            if path.endswith("/appInfoLocalizations"):
                return {"data": [{"attributes": {"locale": "en-US", "subtitle": "Notes"}}]}
            raise AssertionError(path)

        def lookup(app_id, country="ma"):
            if app_id == "222222222":
                return {
                    "name": "Northline",
                    "url": "https://apps.apple.com/ma/app/northline/id222222222?uo=4",
                    "artwork": "https://is1-ssl.mzstatic.com/image/thumb/test/512x512bb.jpg",
                    "category": "Productivity",
                    "description": "Unused because promotional text exists.",
                }
            return {
                "name": "SillySmile Live 4K Walls",
                "url": "https://apps.apple.com/ma/app/sillysmile-live-4k-walls/id6783467232?uo=4",
                "artwork": "https://is1-ssl.mzstatic.com/image/thumb/test/512x512bb.jpg",
                "category": "Graphics & Design",
                "description": "A long public description that must not replace the saved copy.",
            }

        catalog = update_apps.build_from_connect(asc, lookup, lambda app_id, url: "", copies)
        by_id = {app["id"]: app for app in catalog["apps"]}
        self.assertEqual(set(by_id), {"6783467232", "222222222"})
        self.assertTrue(by_id["6783467232"]["featured"])
        self.assertEqual(
            by_id["6783467232"]["description"],
            copies["6783467232"]["description"],
        )
        self.assertEqual(by_id["6783467232"]["icon"], "assets/icons/sillysmile.png")
        self.assertEqual(
            by_id["6783467232"]["url"],
            "https://apps.apple.com/ma/app/sillysmile-live-4k-walls/id6783467232",
        )
        self.assertEqual(by_id["222222222"]["description"], "A quiet notes app for iPhone.")
        self.assertEqual(by_id["222222222"]["category"], "Productivity")
        self.assertFalse(by_id["222222222"]["featured"])
        self.assertNotIn("uo=4", by_id["222222222"]["url"])
        blob = json.dumps(catalog)
        self.assertNotIn("bundleId", blob)
        self.assertNotIn("PRIVATE KEY", blob)

    def test_description_fallback_uses_two_sentences_only(self):
        text = update_apps.first_sentences(
            "First sentence. Second sentence. Third sentence should stay out.\n\nFeatures\n• Invented extra"
        )
        self.assertEqual(text, "First sentence. Second sentence.")

    def test_refuses_to_write_secret_material(self):
        private_key = pem_key()
        document = {
            "apps": [
                {
                    "id": "6783467232",
                    "name": "Example",
                    "description": private_key,
                    "url": "https://apps.apple.com/app/id6783467232",
                    "featured": True,
                    "category": "",
                    "platform": "iOS",
                }
            ],
            "source": "app-store-connect",
        }
        with self.assertRaises(update_apps.CatalogError):
            update_apps.assert_public(document, [private_key])

    def test_token_is_not_sent_to_itunes(self):
        with self.assertRaises(update_apps.CatalogError):
            update_apps.asc_get(mock.Mock(), "https://itunes.apple.com/lookup", None)

    def test_editorial_case_study_fields_stay_public(self):
        record = update_apps.attach_editorial(
            update_apps.public_record(
                "6783467232",
                "SillySmile Live 4K Walls",
                "https://apps.apple.com/ma/app/sillysmile-live-4k-walls/id6783467232",
                "assets/icons/sillysmile.png",
                "An iOS wallpaper experience.",
                "Graphics & Design",
                "iOS",
            ),
            {
                "role": "Independent Developer",
                "focus": "Native iOS work for discovering and browsing 4K and live wallpapers.",
                "technologies": ["Native iOS"],
            },
        )
        self.assertEqual(record["role"], "Independent Developer")
        self.assertIn("4K and live wallpapers", record["focus"])
        self.assertEqual(record["technologies"], ["Native iOS"])
        update_apps.assert_public({"apps": [record], "source": "app-store-connect"}, [])
        record["bundleId"] = "com.example.app"
        with self.assertRaises(update_apps.CatalogError):
            update_apps.assert_public({"apps": [record]}, [])

    def test_write_skips_when_catalog_is_unchanged(self):
        document = {
            "apps": [
                {
                    "category": "Graphics & Design",
                    "description": "Saved copy.",
                    "featured": True,
                    "id": "6783467232",
                    "name": "SillySmile Live 4K Walls",
                    "platform": "iOS",
                    "url": "https://apps.apple.com/ma/app/sillysmile-live-4k-walls/id6783467232",
                }
            ],
            "source": "app-store-connect",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "apps.json"
            output.write_text(json.dumps(document), encoding="utf-8")
            with mock.patch.object(update_apps, "OUTPUT_PATH", output):
                changed = update_apps.write_catalog(dict(document), [])
            self.assertFalse(changed)
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("generatedAt", saved)


class WorkflowTests(unittest.TestCase):
    def test_workflow_keeps_credentials_in_secrets_and_limits_permissions(self):
        text = (ROOT / ".github" / "workflows" / "update-apps.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("cron:", text)
        self.assertIn("contents: write", text)
        self.assertNotIn("write-all", text)
        self.assertNotIn("BEGIN PRIVATE KEY", text)
        self.assertNotIn("pull_request", text)
        for name in (
            "APP_STORE_CONNECT_KEY_ID",
            "APP_STORE_CONNECT_ISSUER_ID",
            "APP_STORE_CONNECT_PRIVATE_KEY",
        ):
            self.assertIn("secrets." + name, text)
        browser = (ROOT / "apps.js").read_text(encoding="utf-8")
        self.assertNotIn("APP_STORE_CONNECT", browser)
        self.assertNotIn("api.appstoreconnect.apple.com", browser)
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("SillySmile", page)
        self.assertNotIn("APP_STORE_CONNECT", page)

    def test_empty_catalog_does_not_wipe_existing_apps(self):
        document = {"apps": [], "source": "app-store-connect"}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "apps.json"
            output.write_text(
                json.dumps({"apps": [{"id": "6783467232"}], "source": "app-store-connect"}),
                encoding="utf-8",
            )
            with mock.patch.object(update_apps, "OUTPUT_PATH", output):
                with self.assertRaises(update_apps.CatalogError):
                    update_apps.write_catalog(document, [])
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["apps"][0]["id"], "6783467232")


if __name__ == "__main__":
    unittest.main()
