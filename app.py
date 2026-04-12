import asyncio
import requests
import re
import sqlite3
import shutil
import os
from playwright.async_api import async_playwright

# ── CONFIGURACIÓN ──────────────────────────────────────────
GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
META_BS_URL = "https://business.facebook.com/latest/inbox/messenger"
COOKIES_FILE = r"C:\xtrategy-adid\Cookies"

# ── Extraer cookies de Facebook desde Chrome ───────────────
def get_facebook_cookies():
    tmp = r"C:\xtrategy-adid\Cookies_tmp"
    shutil.copy2(COOKIES_FILE, tmp)
    conn = sqlite3.connect(tmp)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, value, host_key, path, is_secure, expires_utc
        FROM cookies
        WHERE host_key LIKE '%facebook.com%' OR host_key LIKE '%business.facebook.com%'
    """)
    rows = cursor.fetchall()
    conn.close()
    os.remove(tmp)
    cookies = []
    for row in rows:
        cookies.append({
            "name": row[0],
            "value": row[1],
            "domain": row[2],
            "path": row[3],
            "secure": bool(row[4]),
        })
    return cookies

# ── GHL: obtener contactos sin ad_id ───────────────────────
def get_contacts_without_adid():
    url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Authorization": f"Bearer {GHL_TOKEN}",
        "Version": "2021-07-28"
    }
    params = {
        "locationId": GHL_LOCATION_ID,
        "limit": 100
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    contacts = data.get("contacts", [])
    without_adid = []
    for c in contacts:
        custom_fields = c.get("customFields", [])
        has_adid = any(f.get("value") for f in custom_fields if "ad" in f.get("id", "").lower())
        if not has_adid:
            without_adid.append({
                "id": c["id"],
                "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
            })
    return without_adid

# ── GHL: guardar ad_id ─────────────────────────────────────
def save_adid_to_ghl(contact_id, ad_id):
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {GHL_TOKEN}",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }
    payload = {
        "customFields": [
            {"key": "ad_id", "field_value": ad_id}
        ]
    }
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code

# ── META BS: buscar ad_id por nombre ──────────────────────
async def get_adid_from_meta(page, name):
    try:
        await page.goto(META_BS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        search = page.locator('input[placeholder*="Search"], input[type="search"]').first
        await search.click()
        await search.fill(name)
        await page.wait_for_timeout(2000)

        person = page.locator('text=' + name).first
        await person.click()
        await page.wait_for_timeout(3000)

        html = await page.content()
        matches = re.findall(r'ad_id\.(\d+)', html)
        unique = list(dict.fromkeys(matches))

        if unique:
            print(f"  ✓ {name} → {unique[0]}")
            return unique[0]
        else:
            print(f"  ✗ {name} → sin ad_id")
            return None
    except Exception as e:
        print(f"  ⚠ {name} → error: {e}")
        return None

# ── MAIN ───────────────────────────────────────────────────
async def main():
    print("Extrayendo cookies de Facebook...")
    cookies = get_facebook_cookies()
    print(f"Cookies encontradas: {len(cookies)}")

    print("Obteniendo contactos sin ad_id desde GHL...")
    contacts = get_contacts_without_adid()
    print(f"Contactos sin ad_id: {len(contacts)}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        for contact in contacts:
            name = contact["name"]
            contact_id = contact["id"]
            print(f"Procesando: {name}")

            ad_id = await get_adid_from_meta(page, name)

            if ad_id:
                status = save_adid_to_ghl(contact_id, ad_id)
                print(f"  → Guardado en GHL (status {status})")

            await page.wait_for_timeout(1000)

        await browser.close()

    print("\n✅ Proceso completado")

if __name__ == "__main__":
    asyncio.run(main())
