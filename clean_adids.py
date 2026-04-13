import requests

# ── CONFIGURACIÓN ──────────────────────────────────────────
GHL_TOKEN = "pit-08166086-17f2-4dcc-88d2-8f065adae15c"
GHL_LOCATION_ID = "6VJ6jJ4IxhkiJLzHZUcx"
AD_ID_FIELD_ID = "yDJQa5wnMZBKQRjvvIuA"
WRONG_AD_ID = "120240219389700179"

# ── GHL: obtener todos los contactos ──────────────────────
def get_all_contacts():
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
        print(f"  Obtenidos: {len(all_contacts)} contactos...")

        meta = data.get("meta", {})
        if not meta.get("nextPage"):
            break
        start_after = meta.get("startAfter")
        start_after_id = meta.get("startAfterId")
        if not start_after:
            break

    return all_contacts

# ── GHL: borrar ad_id de un contacto ──────────────────────
def clear_adid(contact_id, name):
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {GHL_TOKEN}",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }
    payload = {"customFields": [{"key": "ad_id", "field_value": ""}]}
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"  ✓ Limpiado: {name}")
    else:
        print(f"  ✗ Error {response.status_code}: {name}")
    return response.status_code

# ── MAIN ───────────────────────────────────────────────────
def main():
    print("Obteniendo todos los contactos...")
    contacts = get_all_contacts()
    print(f"Total obtenidos: {len(contacts)}\n")

    to_clean = []
    for c in contacts:
        custom_fields = c.get("customFields", [])
        ad_id_field = next((f for f in custom_fields if f.get("id") == AD_ID_FIELD_ID), None)
        if ad_id_field:
            value = str(ad_id_field.get("value", "")).strip()
            if value == WRONG_AD_ID:
                to_clean.append({
                    "id": c["id"],
                    "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                })

    print(f"Contactos con Ad ID incorrecto ({WRONG_AD_ID}): {len(to_clean)}\n")

    if not to_clean:
        print("No hay contactos para limpiar.")
        return

    print("Limpiando Ad IDs incorrectos...")
    cleaned = 0
    errors = 0
    for c in to_clean:
        status = clear_adid(c["id"], c["name"])
        if status == 200:
            cleaned += 1
        else:
            errors += 1

    print(f"\n✅ Completado — Limpiados: {cleaned} | Errores: {errors}")
    print("Estos contactos quedan listos para reprocesar con app.py")

if __name__ == "__main__":
    main()
