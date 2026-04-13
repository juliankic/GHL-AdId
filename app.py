import asyncio
import requests
import re
from playwright.async_api import async_playwright

# ── CONFIGURACION ──────────────────────────────────────────
GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
META_BS_URL = "https://business.facebook.com/latest/inbox/messenger"
LEAD_SOURCE_FIELD_ID = "iUwcdfMseINgp70KbIsZ"
AD_ID_FIELD_ID = "yDJQa5wnMZBKQRjvvIuA"

# ── GHL: obtener contactos Meta Ads sin ad_id ──────────────
def get_contacts_without_adid():
    base_url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Authorization": f"Bearer {GHL_TOKEN}",
        "Version": "2021-07-28"
    }
    all_contacts = []
    start_after = None
    start_after_id = None

    while True:
        params = {"locationId": GHL_LOCATION_ID, "limit": 100}
        if start_after:
            params["startAfter"] = start_after
            params["startAfterId"] = start_after_id

        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()
        contacts = data.get("contacts", [])
        if not contacts:
            break
        all_contacts.extend(contacts)
        print("  Obtenidos: " + str(len(all_contacts)) + " contactos...")

        meta = data.get("meta", {})
        if not meta.get("nextPage"):
            break
        start_after = meta.get("startAfter")
        start_after_id = meta.get("startAfterId")
        if not start_after:
            break

    without_adid = []
    for c in all_contacts:
        custom_fields = c.get("customFields", [])
        lead_source_field = next((f for f in custom_fields if f.get("id") == LEAD_SOURCE_FIELD_ID), None)
        lead_source_value = lead_source_field.get("value", []) if lead_source_field else []
        if isinstance(lead_source_value, str):
            lead_source_value = [lead_source_value]
        is_meta_ads = any("meta" in str(v).lower() for v in lead_source_value)
        ad_id_field = next((f for f in custom_fields if f.get("id") == AD_ID_FIELD_ID), None)
        has_adid = ad_id_field and ad_id_field.get("value")
        if is_meta_ads and not has_adid:
            without_adid.append({
                "id": c["id"],
                "name": (c.get("firstName", "") + " " + c.get("lastName", "")).strip()
            })

    print("Total: " + str(len(all_contacts)) + " | Meta Ads sin ad_id: " + str(len(without_adid)))
    return without_adid

# ── GHL: guardar ad_id ─────────────────────────────────────
def save_adid_to_ghl(contact_id, ad_id):
    url = "https://services.leadconnectorhq.com/contacts/" + contact_id
    headers = {
        "Authorization": "Bearer " + GHL_TOKEN,
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }
    payload = {"customFields": [{"key": "ad_id", "field_value": ad_id}]}
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code

# ── META BS: buscar ad_id por nombre ──────────────────────
async def get_adid_from_meta(page, name):
    try:
        await page.goto(META_BS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        search = page.locator('input[placeholder*="Search"], input[type="search"]').first
        await search.click()
        await search.clear()
        await search.fill(name)
        await page.wait_for_timeout(4000)

        first_name = name.split()[0].lower()

        box = await page.evaluate("""
            (firstName) => {
                const allDivs = Array.from(document.querySelectorAll('div'));
                const match = allDivs.find(el =>
                    el.children.length === 0 &&
                    el.textContent.trim().toLowerCase().includes(firstName) &&
                    el.getBoundingClientRect().width > 50
                );
                if (match) {
                    const rect = match.getBoundingClientRect();
                    return {
                        x: rect.x + rect.width / 2,
                        y: rect.y + rect.height / 2,
                        text: match.textContent.trim(),
                        width: rect.width,
                        height: rect.height
                    };
                }
                return null;
            }
        """, first_name)

        if not box:
            print("  X " + name + " -> no encontrado en Meta BS")
            return None

        print("  DEBUG click en: '" + str(box['text']) + "' coords=(" + str(round(box['x'])) + ", " + str(round(box['y'])) + ")")

        await page.mouse.click(box['x'], box['y'])
        await page.wait_for_timeout(4000)

        for scroll_pos in [400, 800, 1200]:
            await page.evaluate("""
                (pos) => {
                    const panels = document.querySelectorAll('[role="complementary"]');
                    panels.forEach(p => p.scrollTop = pos);
                }
            """, scroll_pos)
            await page.wait_for_timeout(1200)

            try:
                html = await page.locator('[role="complementary"]').last.inner_html(timeout=2000)
                matches = re.findall(r'ad_id\.(\d+)', html)
                if matches:
                    ad_id = matches[0]
                    print("  OK " + name + " -> " + ad_id)
                    return ad_id
            except:
                pass

        print("  X " + name + " -> sin ad_id en Labels")
        return None

    except Exception as e:
        print("  ERROR " + name + " -> " + str(e))
        return None

# ── MAIN ───────────────────────────────────────────────────
async def main():
    print("Obteniendo contactos Meta Ads sin ad_id...")
    contacts = get_contacts_without_adid()
    print("Total a procesar: " + str(len(contacts)))

    if not contacts:
        print("No hay contactos para procesar.")
        return

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
            print("Procesando: " + name)
            ad_id = await get_adid_from_meta(page, name)
            if ad_id:
                status = save_adid_to_ghl(contact_id, ad_id)
                print("  -> Guardado en GHL (status " + str(status) + ")")
            await page.wait_for_timeout(1000)

        await browser.close()

    print("Proceso completado")

if __name__ == "__main__":
    asyncio.run(main())
