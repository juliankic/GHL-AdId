import asyncio
import requests
import re
from playwright.async_api import async_playwright

GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
META_BS_URL = "https://business.facebook.com/latest/inbox/messenger"
LEAD_SOURCE_FIELD_ID = "iUwcdfMseINgp70KbIsZ"
AD_ID_FIELD_ID = "yDJQa5wnMZBKQRjvvIuA"

def get_contacts_without_adid():
    base_url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Authorization": "Bearer " + GHL_TOKEN,
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

async def get_adid_from_meta(page, name):
    try:
        await page.goto(META_BS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        search = page.locator('input[placeholder*="Search"], input[type="search"]').first
        await search.click()
        await search.clear()
        await search.fill(name)
        await page.wait_for_timeout(4000)

        # Leer el HTML del panel izquierdo despues de buscar
        # El label ad_id ya es visible en la lista sin necesidad de abrir la conversacion
        left_panel_html = await page.evaluate("""
            () => {
                const allDivs = Array.from(document.querySelectorAll('div'));
                const leftPanel = allDivs.find(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.x < 50 && rect.width > 200 && rect.height > 400;
                });
                return leftPanel ? leftPanel.innerHTML : document.body.innerHTML;
            }
        """)

        matches = re.findall(r'ad_id\.(\d+)', left_panel_html)
        if matches:
            ad_id = matches[0]
            print("  OK " + name + " -> " + ad_id + " (desde lista)")
            return ad_id

        # Fallback: hover sobre el label ad_id visible y leer tooltip
        try:
            ad_label = page.locator('text=/ad_id\\.\\d+/').first
            label_text = await ad_label.inner_text(timeout=3000)
            matches = re.findall(r'ad_id\.(\d+)', label_text)
            if matches:
                ad_id = matches[0]
                print("  OK " + name + " -> " + ad_id + " (desde label visible)")
                return ad_id
        except:
            pass

        # Fallback: mover cursor encima del icono ad_id para que aparezca el tooltip
        try:
            ad_icon = page.locator('[aria-label*="ad_id"], text="ad_id...."').first
            await ad_icon.hover(timeout=3000)
            await page.wait_for_timeout(1500)
            tooltip_html = await page.content()
            matches = re.findall(r'ad_id\.(\d+)', tooltip_html)
            unique = list(dict.fromkeys(matches))
            if unique:
                ad_id = unique[0]
                print("  OK " + name + " -> " + ad_id + " (desde tooltip)")
                return ad_id
        except:
            pass

        print("  X " + name + " -> sin ad_id encontrado")
        return None

    except Exception as e:
        print("  ERROR " + name + " -> " + str(e))
        return None

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
