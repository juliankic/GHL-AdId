async def get_adid_from_meta(page, name):
    try:
        await page.goto(META_BS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Buscar con nombre completo primero, luego solo primer nombre
        search_terms = [name, name.split()[0]]
        
        for search_term in search_terms:
            search = page.locator('input[placeholder*="Search"], input[type="search"]').first
            await search.click()
            await search.triple_click()
            await search.fill(search_term)
            await page.wait_for_timeout(2000)

            # Buscar en sección People
            people_section = page.locator('text=People').first
            try:
                await people_section.wait_for(timeout=3000)
                # Click en primer resultado de People
                first_person = page.locator('[data-testid*="search"] a, [class*="search"] a').first
                await first_person.click(timeout=3000)
                await page.wait_for_timeout(3000)
                break
            except:
                # Intentar click directo en el nombre
                try:
                    person = page.locator(f'text="{search_term}"').first
                    await person.click(timeout=3000)
                    await page.wait_for_timeout(3000)
                    break
                except:
                    continue

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
