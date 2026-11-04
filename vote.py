"""Test manuel des formulaires de vote Root-Top pour Tulipe.

Une seule soumission par topsite et par exécution. Ne contourne pas les limites IP.
"""
import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

PSEUDO = "Tulipe"
SITES = {
    "justmarried-1333": "http://www.root-top.com/topsite/justmarried/in.php?IDmark=1333",
    "virtu4ldreaiviz-5970": "http://www.root-top.com/topsite/virtu4ldreaiviz/in.php?IDmark=5970",
    "virtu4lgames-7046": "http://www.root-top.com/topsite/virtu4lgames/in.php?IDmark=7046",
    "gilgamesh-8765": "http://www.root-top.com/topsite/gilgamesh/in.php?IDmark=8765",
}

async def tester(page, nom, url):
    print(f"\n===== {nom} =====")
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print("HTTP initial :", response.status if response else "sans réponse")
        await page.screenshot(path=f"captures/{nom}-avant.png", full_page=True)

        # Repérage du formulaire : un input texte/identifiant et un bouton de vote.
        candidates = page.locator('input[type="text"], input:not([type])')
        nb = await candidates.count()
        if nb != 1:
            print(f"NON SOUMIS : {nb} champs texte trouvés (attendu : 1).")
            return
        await candidates.first.fill(PSEUDO)
        bouton = page.get_by_role("button", name=re.compile("entrer et voter", re.I))
        if await bouton.count() != 1:
            bouton = page.locator('input[type="submit"][value*="voter" i]')
        if await bouton.count() != 1:
            print("NON SOUMIS : bouton de vote introuvable ou ambigu.")
            return

        await bouton.first.click(timeout=15000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            print("Navigation non confirmée ; récupération de l'état affiché.")
        await page.screenshot(path=f"captures/{nom}-apres.png", full_page=True)
        print("URL après clic :", page.url)
        print("Résultat affiché :", (await page.locator("body").inner_text())[:900].replace("\n", " "))
        print("Soumission effectuée ; vérifier le texte ou la capture pour confirmer le comptage.")
    except Exception as exc:
        print(f"ÉCHEC : {type(exc).__name__} : {exc}")
        try:
            await page.screenshot(path=f"captures/{nom}-erreur.png", full_page=True)
        except Exception:
            pass

async def main():
    Path("captures").mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for nom, url in SITES.items():
                page = await browser.new_page(locale="fr-FR")
                try:
                    await tester(page, nom, url)
                finally:
                    await page.close()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
