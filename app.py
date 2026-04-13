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

        # Click usando la clase exacta del div del nombre
        try:
            result = page.locator('div.x1n2onr6.xozqiw3.x14atkfc.xt7fyl5.x78zum5.x1iyjqo2.xdj266r').first
            await result.click(timeout=5000)
            await page.wait_for_timeout(3000)
        except:
            try:
                # Fallback: buscar por texto parcial case-insensitive
                first_name = name.split()[0]
                result = page.get_by_text(first_name, exact=False).first
                await result.click(timeout=5000)
                await page.wait_for_timeout(3000)
            except:
                print(f"  ✗ {name} → no encontrado en Meta BS")
                return None

        # Scroll down panel derecho para cargar Labels
        await page.evaluate("""
            const panels = document.querySelectorAll('[role="complementary"]');
            panels.forEach(p => p.scrollTop = 600);
        """)
        await page.wait_for_timeout(2000)

        # Leer Labels del panel derecho
        try:
            labels_container = page.locator('text="Labels"').locator('xpath=../../..')
            labels_html = await labels_container.inner_html(timeout=3000)
            matches = re.findall(r'ad_id\.(\d+)', labels_html)
            if matches:
                ad_id = matches[0]
                print(f"  ✓ {name} → {ad_id}")
                return ad_id
        except:
            pass

        # Fallback: buscar en panel derecho completo
        try:
            right_panel = page.locator('[role="complementary"]').last
            panel_text = await right_panel.inner_text(timeout=3000)
            matches = re.findall(r'ad_id\.(\d+)', panel_text)
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
