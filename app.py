import asyncio
import requests
import re
from playwright.async_api import async_playwright

# ── CONFIGURACIÓN ──────────────────────────────────────────
GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
META_BS_URL = "https://business.facebook.com/latest/inbox/messenger"
SMART_LIST_URL = "https://app.leadconnectorhq.com/v2/location/6VJ6jJ4IxhkiJLzHZUcx/contacts/smart_list/jKXOXcMONZ567Rcn47DG"

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

# ── GHL: extraer contactos de Smart List via Playwright ────
async def get_contacts_from_smartlist(page):
    print("Navegando a Smart List en GHL...")
    await page.goto(SMART_LIST_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)

    contacts = []
    while True:
        rows = await page.query_selector_all("tr.n-data-table-tr")
        for row in rows:
            try:
                name_el = await row.query_selector("td:first-child span.n-ellipsis")
                if not name_el:
                    name_el = await row.query_selector("td:first-child")
                if not name_el:
                    continue
                name = (await name_el.inner_text()).strip()
                if not name:
                    continue

                # Obtener contact ID del link
                link_el = await row.query_selector("a[href*='/contacts/']")
                contact_id = None
                if link_el:
                    href = await link_el.get_attribute("href")
                    match = re.search(r'/contacts/([a-zA-Z0-9]+)', href)
                    if match:
                        contact_id = match.group(1)

                if name and contact_id:
                    contacts.append({"id": contact_id, "name": name})
                    print(f"  → {name} ({contact_id})")
            except:
                continue

        # Verificar si hay siguiente página
        next_btn = await page.query_selector("button.n-pagination-item--next:not([disabled])")
        if next_btn:
            await next_btn.click()
            await page.wait_for_timeout(3000)
        else:
            break

    print(f"Total contactos en Smart List: {len(contacts)}")
    return contacts

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
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\JC\AppData\Local\Google\Chrome\User Data\Profile 20",
            executable_path=r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            headless=False,
            channel="chrome",
            args=["--profile-directory=Profile 20"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Paso 1: extraer contactos de Smart List
        contacts = await get_contacts_from_smartlist(page)
        print(f"\nTotal a procesar: {len(contacts)}\n")

        if not contacts:
            print("No se encontraron contactos en la Smart List.")
            await browser.close()
            return

        # Paso 2: para cada contacto buscar ad_id en Meta BS
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
