import asyncio
import requests
import re
from playwright.async_api import async_playwright

# ── CONFIGURACIÓN ──────────────────────────────────────────
GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
META_BS_URL = "https://business.facebook.com/latest/inbox/messenger"

# ── GHL: obtener contactos sin ad_id ───────────────────────
def get_contacts_without_adid():
    url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Authorization": f"Bearer {GHL_TOKEN}",
        "Version": "2021-07-28"
    }
    all_contacts = []
    page = 1
    while True:
        params = {
            "locationId": GHL_LOCATION_ID,
            "limit": 100,
            "page": page
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        contacts = data.get("contacts", [])
        if not contacts:
            break
        all_contacts.extend(contacts)
        if len(contacts) < 100:
            break
        page += 1

    without_adid = []
    for c in all_contacts:
        custom_fields = c.get("customFields", [])
        ad_id_field = next((f for f in custom_fields if "ad_id" in f.get("id", "").lower() or "ad_id" in f.get("key", "").lower()), None)
        has_adid = ad_id_field and ad_id_field.get("value")
        if not has_adid:
            without_adid.append({
                "id": c["id"],
                "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
            })

    print(f"Total contactos: {len(all_contacts)} | Sin ad_id: {len(without_adid)}")
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
    print("Obteniendo contactos sin ad_id desde GHL...")
    contacts = get_contacts_without_adid()
    print(f"Total a procesar: {len(contacts)}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\JC\AppData\Local\Google\Chrome\User Data\Profile 20",
            executable_path=r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            headless=False,
            channel="chrome",
            args=["--profile-directory=Profile 20"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

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
