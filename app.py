import asyncio
import requests
from playwright.async_api import async_playwright

# ── CONFIGURACIÓN ──────────────────────────────────────────
GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
CHROME_USER_DATA = r"C:\Users\JC\AppData\Local\Google\Chrome\User Data"
CHROME_PROFILE = "Default"
META_BS_URL = "https://business.facebook.com/latest/inbox/messenger"

# ── GHL: obtener contactos sin ad_id ───────────────────────
def get_contacts_without_adid():
    url = f"https://services.leadconnectorhq.com/contacts/"
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
        
        # Buscar en la barra de búsqueda
        search = page.locator('input[placeholder*="Search"], input[type="search"]').first
        await search.click()
        await search.fill(name)
        await page.wait_for_timeout(2000)
        
        # Click en primera persona encontrada
        person = page.locator('text=' + name).first
        await person.click()
        await page.wait_for_timeout(2000)
        
        # Extraer ad_id del HTML completo
        html = await page.content()
        import re
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
    print(f"Encontrados: {len(contacts)} contactos\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA,
            executable_path=CHROME_PATH,
            headless=False,
            args=["--profile-directory=" + CHROME_PROFILE]
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
