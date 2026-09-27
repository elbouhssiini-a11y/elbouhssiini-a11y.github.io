#!/usr/bin/env python3
"""Build public apps.json from App Store Connect.

Credentials are read only from the process environment. They are never
written to apps.json, icon files, or logs.
"""

import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import jwt
import requests

ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "data" / "app-copy.json"
OUTPUT_PATH = ROOT / "apps.json"
ICON_DIR = ROOT / "assets" / "icons"
ASC_BASE = "https://api.appstoreconnect.apple.com"
ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
REQUIRED_ENV = (
    "APP_STORE_CONNECT_KEY_ID",
    "APP_STORE_CONNECT_ISSUER_ID",
    "APP_STORE_CONNECT_PRIVATE_KEY",
)
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "APP_STORE_CONNECT_",
)
MAX_ICON_BYTES = 2_000_000
SENTENCE_LIMIT = 2
TEXT_LIMIT = 320


class CatalogError(Exception):
    """A safe, loggable failure that does not include credential values."""


def load_copy():
    if not COPY_PATH.is_file():
        return {}
    with COPY_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise CatalogError("data/app-copy.json must be an object keyed by app ID.")
    return data


def require_credentials():
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name, "").strip()]
    if missing:
        raise CatalogError(
            "Missing required environment variables: " + ", ".join(missing)
        )
    key = os.environ["APP_STORE_CONNECT_PRIVATE_KEY"].replace("\\n", "\n").strip()
    if "PRIVATE KEY" not in key:
        raise CatalogError("APP_STORE_CONNECT_PRIVATE_KEY is not a PEM private key.")
    return {
        "key_id": os.environ["APP_STORE_CONNECT_KEY_ID"].strip(),
        "issuer_id": os.environ["APP_STORE_CONNECT_ISSUER_ID"].strip(),
        "private_key": key,
    }


def make_token(key_id, issuer_id, private_key):
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": issuer_id,
            "iat": now,
            "exp": now + 15 * 60,
            "aud": "appstoreconnect-v1",
        },
        private_key,
        algorithm="ES256",
        headers={"alg": "ES256", "kid": key_id, "typ": "JWT"},
    )
    if isinstance(token, bytes):
        token = token.decode("ascii")
    return token


def asc_get(session, path, params=None):
    url = path if path.startswith("https://") else ASC_BASE + path
    host = urllib.parse.urlparse(url).hostname
    if host != "api.appstoreconnect.apple.com":
        raise CatalogError("Refusing to send the App Store Connect token to another host.")
    try:
        response = session.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        raise CatalogError(
            "App Store Connect request failed (" + type(exc).__name__ + ")."
        ) from None
    if response.status_code in (401, 403):
        raise CatalogError(
            "App Store Connect rejected the token (" + str(response.status_code) + ")."
        )
    if not response.ok:
        safe_path = urllib.parse.urlparse(url).path
        raise CatalogError(
            "App Store Connect request failed ("
            + str(response.status_code)
            + ") for "
            + safe_path
            + "."
        )
    return response.json()


def public_get(url, params=None):
    host = urllib.parse.urlparse(url).hostname
    if host not in ("itunes.apple.com",):
        raise CatalogError("Refusing an unexpected public lookup host.")
    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
            headers={"Accept": "application/json"},
        )
    except requests.RequestException as exc:
        raise CatalogError("Public lookup failed (" + type(exc).__name__ + ").") from None
    if not response.ok:
        raise CatalogError("Public lookup failed (" + str(response.status_code) + ").")
    return response.json()


def lookup_store(app_id, country="ma"):
    payload = public_get(
        ITUNES_LOOKUP,
        {"id": app_id, "country": country, "entity": "software"},
    )
    for item in payload.get("results") or []:
        if str(item.get("trackId")) == str(app_id) and item.get("kind") == "software":
            return {
                "name": item.get("trackName") or "",
                "url": item.get("trackViewUrl") or "",
                "artwork": item.get("artworkUrl512") or item.get("artworkUrl100") or "",
                "category": item.get("primaryGenreName") or "",
                "description": item.get("description") or "",
            }
    return {}


def pick_attributes(records, primary_locale):
    by_locale = {}
    for record in records or []:
        attributes = record.get("attributes") or {}
        locale = attributes.get("locale")
        if locale:
            by_locale[locale] = attributes
    for locale in (primary_locale, "en-US", "en-GB"):
        if locale in by_locale:
            return by_locale[locale]
    if by_locale:
        return next(iter(by_locale.values()))
    return {}


def first_sentences(text, limit=SENTENCE_LIMIT):
    paragraph = (text or "").strip().split("\n\n", 1)[0]
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    if not paragraph:
        return ""
    pieces = re.findall(r"[^.!?]+[.!?]?", paragraph)
    chosen = []
    for piece in pieces:
        sentence = piece.strip()
        if sentence:
            chosen.append(sentence)
        if len(chosen) >= limit:
            break
    result = " ".join(chosen).strip()
    if len(result) > TEXT_LIMIT:
        shortened = result[:TEXT_LIMIT].rsplit(" ", 1)[0].rstrip(".,;:")
        result = shortened + "."
    return result


def choose_description(app_id, copy, promo, subtitle, store_description, name):
    override = ((copy.get(app_id) or {}).get("description") or "").strip()
    if override:
        return override
    for source in (promo, subtitle):
        short = first_sentences(source or "")
        if short:
            return short
    short = first_sentences(store_description or "")
    if short:
        return short
    clean_name = (name or "This app").strip()
    return clean_name + " is available on the App Store."


def clean_store_url(url, app_id):
    parsed = urllib.parse.urlparse(url or "")
    if (
        parsed.scheme == "https"
        and parsed.hostname == "apps.apple.com"
        and "id" + str(app_id) in parsed.path
    ):
        return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
    return "https://apps.apple.com/app/id" + str(app_id)


def safe_local_icon(path):
    if not isinstance(path, str):
        return ""
    if not re.fullmatch(r"assets/icons/[A-Za-z0-9._-]+", path):
        return ""
    dest = (ROOT / path).resolve()
    if dest.parent != ICON_DIR.resolve() or not dest.is_file():
        return ""
    return path


def allowed_artwork(url):
    parsed = urllib.parse.urlparse(url or "")
    host = parsed.hostname or ""
    return parsed.scheme == "https" and (
        host == "mzstatic.com" or host.endswith(".mzstatic.com")
    )


def download_icon(app_id, artwork_url):
    if not re.fullmatch(r"\d{6,}", str(app_id)) or not allowed_artwork(artwork_url):
        return ""
    try:
        response = requests.get(artwork_url, timeout=30, stream=True)
    except requests.RequestException:
        return ""
    if not response.ok:
        return ""
    data = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        data.extend(chunk)
        if len(data) > MAX_ICON_BYTES:
            return ""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        suffix = ".png"
    elif data.startswith(b"\xff\xd8\xff"):
        suffix = ".jpg"
    else:
        return ""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    dest = (ICON_DIR / (str(app_id) + suffix)).resolve()
    if dest.parent != ICON_DIR.resolve():
        raise CatalogError("Refusing to write an icon outside assets/icons.")
    dest.write_bytes(data)
    return "assets/icons/" + dest.name


def choose_icon(app_id, copy, artwork_url, download):
    local = safe_local_icon((copy.get(app_id) or {}).get("icon"))
    if local:
        return local
    return download(app_id, artwork_url) if artwork_url else ""


def choose_name(app_id, copy, connect_name, store_name):
    override = ((copy.get(app_id) or {}).get("name") or "").strip()
    if override:
        return override
    return (connect_name or store_name or "").strip()


def public_record(app_id, name, url, icon, description, category, platform):
    if not re.fullmatch(r"\d{6,}", str(app_id)):
        return None
    name = (name or "").strip()
    description = re.sub(r"\s+", " ", description or "").strip()
    if not name or not description:
        return None
    record = {
        "category": (category or "").strip(),
        "description": description,
        "featured": False,
        "id": str(app_id),
        "name": name,
        "platform": "iOS" if platform == "iOS" else "",
        "url": clean_store_url(url, app_id),
    }
    if icon:
        record["icon"] = icon
    return record


def apply_featured(apps, copies):
    preferred = [
        app["id"]
        for app in apps
        if (copies.get(app["id"]) or {}).get("featured") is True
    ]
    chosen = preferred[0] if preferred else (apps[0]["id"] if apps else None)
    for app in apps:
        app["featured"] = app["id"] == chosen
    apps.sort(key=lambda app: (not app["featured"], app["name"].casefold(), app["id"]))


def assert_public(document, secrets):
    blob = json.dumps(document, ensure_ascii=False)
    for marker in SECRET_MARKERS:
        if marker in blob:
            raise CatalogError("Refusing to write apps.json because it contains private material.")
    for secret in secrets:
        if secret and secret in blob:
            raise CatalogError("Refusing to write apps.json because it contains private material.")
    for app in document.get("apps") or []:
        extra = set(app) - {
            "category",
            "description",
            "featured",
            "icon",
            "id",
            "name",
            "platform",
            "url",
        }
        if extra:
            raise CatalogError("Refusing to write apps.json with unexpected fields.")
        if "bundleId" in json.dumps(app):
            raise CatalogError("Refusing to write a bundle ID into apps.json.")


def same_catalog(previous, document):
    if not previous:
        return False
    return previous.get("source") == document.get("source") and previous.get("apps") == document.get("apps")


def write_catalog(document, secrets):
    assert_public(document, secrets)
    previous = None
    if OUTPUT_PATH.is_file():
        with OUTPUT_PATH.open(encoding="utf-8") as handle:
            previous = json.load(handle)
    if not document.get("apps") and previous and previous.get("apps"):
        raise CatalogError("Refusing to replace the published app list with an empty one.")
    if same_catalog(previous, document):
        print("No app changes.")
        return False
    document["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    assert_public(document, secrets)
    temporary = OUTPUT_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT_PATH)
    print("Updated apps.json (" + str(len(document["apps"])) + " apps).")
    return True


def connect_metadata(asc, app):
    attributes = app.get("attributes") or {}
    app_id = str(app.get("id") or "")
    primary = attributes.get("primaryLocale") or "en-US"
    versions = asc(
        "/v1/apps/" + app_id + "/appStoreVersions",
        {
            "filter[platform]": "IOS",
            "filter[appStoreState]": "READY_FOR_SALE",
            "limit": "1",
        },
    )
    version_rows = versions.get("data") or []
    if not version_rows:
        return None
    version_id = version_rows[0].get("id")
    localizations = asc(
        "/v1/appStoreVersions/" + str(version_id) + "/appStoreVersionLocalizations",
        {"limit": "50"},
    )
    version_text = pick_attributes(localizations.get("data") or [], primary)
    subtitle = ""
    localized_name = ""
    category_enum = ""
    infos = asc("/v1/apps/" + app_id + "/appInfos", {"limit": "10"})
    info_rows = infos.get("data") or []
    info = next(
        (
            row
            for row in info_rows
            if (row.get("attributes") or {}).get("appStoreState") == "READY_FOR_DISTRIBUTION"
        ),
        info_rows[0] if info_rows else None,
    )
    if info:
        category_enum = (info.get("attributes") or {}).get("primaryCategory") or ""
        info_localizations = asc(
            "/v1/appInfos/" + str(info.get("id")) + "/appInfoLocalizations",
            {"limit": "50"},
        )
        info_text = pick_attributes(info_localizations.get("data") or [], primary)
        subtitle = info_text.get("subtitle") or ""
        localized_name = info_text.get("name") or ""
    return {
        "name": localized_name or attributes.get("name") or "",
        "promo": version_text.get("promotionalText") or "",
        "subtitle": subtitle,
        "description": version_text.get("description") or "",
        "category_enum": category_enum if isinstance(category_enum, str) else "",
    }


def human_category(value):
    if not value:
        return ""
    return value.replace("_", " ").title().replace(" And ", " and ")


def build_from_connect(asc, lookup, download, copies):
    apps = []
    payload = asc("/v1/apps", {"limit": "200"})
    rows = list(payload.get("data") or [])
    next_url = ((payload.get("links") or {}).get("next"))
    pages = 0
    while next_url and pages < 10:
        pages += 1
        payload = asc(next_url, None)
        rows.extend(payload.get("data") or [])
        next_url = ((payload.get("links") or {}).get("next"))
    for row in rows:
        app_id = str(row.get("id") or "")
        if not re.fullmatch(r"\d{6,}", app_id):
            continue
        meta = connect_metadata(asc, row)
        if not meta:
            continue
        store = {}
        try:
            store = lookup(app_id)
        except CatalogError:
            store = {}
        copy = copies.get(app_id) or {}
        name = choose_name(app_id, copies, meta["name"], store.get("name"))
        description = choose_description(
            app_id,
            copies,
            meta["promo"],
            meta["subtitle"],
            meta["description"] or store.get("description") or "",
            name,
        )
        category = (store.get("category") or "").strip() or human_category(meta["category_enum"])
        icon = choose_icon(app_id, copies, store.get("artwork") or "", download)
        url = (copy.get("url") or "").strip() or store.get("url") or ""
        record = public_record(app_id, name, url, icon, description, category, "iOS")
        if record:
            apps.append(record)
    apply_featured(apps, copies)
    return {"apps": apps, "source": "app-store-connect"}


def build_bootstrap(lookup, copies):
    apps = []
    for app_id, copy in copies.items():
        if not re.fullmatch(r"\d{6,}", str(app_id)):
            continue
        store = lookup(str(app_id))
        name = choose_name(app_id, copies, "", store.get("name"))
        description = choose_description(
            app_id,
            copies,
            "",
            "",
            store.get("description") or "",
            name,
        )
        icon = safe_local_icon(copy.get("icon"))
        record = public_record(
            app_id,
            name,
            (copy.get("url") or store.get("url") or ""),
            icon,
            description,
            store.get("category") or "",
            "iOS",
        )
        if record:
            apps.append(record)
    apply_featured(apps, copies)
    return {"apps": apps, "source": "public-listing"}


def fetch_catalog():
    creds = require_credentials()
    token = make_token(creds["key_id"], creds["issuer_id"], creds["private_key"])
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    session.headers["Accept"] = "application/json"

    def asc(path, params):
        return asc_get(session, path, params)

    catalog = build_from_connect(asc, lookup_store, download_icon, load_copy())
    secrets = [creds["key_id"], creds["issuer_id"], creds["private_key"], token]
    write_catalog(catalog, secrets)
    session.close()


def bootstrap():
    catalog = build_bootstrap(lookup_store, load_copy())
    write_catalog(catalog, [])


def main(argv):
    try:
        if "--bootstrap" in argv:
            bootstrap()
        else:
            fetch_catalog()
    except CatalogError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print("App update failed (" + type(exc).__name__ + ").", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
