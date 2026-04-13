async def get_adid_from_meta(page, name):
    try:
        await page.goto(META_BS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Buscar contacto
        search = page.locator('input[placeholder*="Search"], input[type="search"]').first
        await search.click()
        await search.clear()
        await search.fill(name)
        await page.wait_for_timeout(2500)

        # Click en el primer resultado que aparezca (sin importar mayúsculas)
        try:
            # Buscar por nombre parcial case-insensitive en la lista
            first_result = page.locator(f'[role="option"]:first-child, ul li:first-child, [data-testid*="conversation"]:first-child').first
            await first_result.click(timeout=5000)
            await page.wait_for_timeout(3000)
        except:
            try:
                # Fallback: click en cualquier elemento que contenga el primer nombre
                first_name = name.split()[0].lower()
                result = page.locator(f'text=/(?i){first_name}/').first
                await result.click(timeout=5000)
                await page.wait_for_timeout(3000)
            except:
                print(f"  ✗ {name} → no encontrado en Meta BS")
                return None

        # Scroll down panel derecho para cargar Labels
        await page.keyboard.press("Tab")
        await page.evaluate("""
            const panels = document.querySelectorAll('[role="complementary"], [data-pagelet="rightRail"]');
            panels.forEach(p => p.scrollTop = 600);
        """)
        await page.wait_for_timeout(2000)

        # Leer Labels del panel derecho
        try:
            labels_html = await page.locator('text="Labels"').locator('xpath=../../..').inner_html(timeout=3000)
            matches = re.findall(r'ad_id\.(\d+)', labels_html)
            if matches:
                ad_id = matches[0]
                print(f"  ✓ {name} → {ad_id}")
                return ad_id
        except:
            pass

        # Fallback: buscar ad_id en cualquier elemento del panel derecho
        try:
            page_text = await page.locator('[role="complementary"]').last.inner_text(timeout=3000)
            matches = re.findall(r'ad_id\.(\d+)', page_text)
            if matches:
                ad_id = matches[0]
                print(f"  ✓ {name} → {ad_id} (fallback)")
                return ad_id
        except:
            pass

        print(f"  ✗ {name} → sin ad_id en Labels")
        return None

    except Exception as e:
        print(f"  ⚠ {name} → error: {e}")
        return None
