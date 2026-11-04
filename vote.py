import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'http://www.root-top.com/topsite/justmarried/in.php?IDmark=1333'
PSEUDO = 'Tulipe'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale='fr-FR')
        try:
            response = await page.goto(URL, wait_until='domcontentloaded', timeout=30000)
            print(f'Page HTTP : {response.status if response else "aucune réponse"}')
            print('URL affichée :', page.url)
            # Capture avant tentative pour diagnostiquer les différences entre navigateurs.
            await page.screenshot(path='avant.png', full_page=True)
            field = page.get_by_text('Identifiant du votant', exact=False)
            if await field.count() == 0:
                print('Libellé introuvable : vérification des champs texte disponibles.')
            inputs = page.locator('input[type="text"], input:not([type])')
            if await inputs.count() != 1:
                raise RuntimeError(f'Formulaire ambigu : {await inputs.count()} champs texte trouvés. Vérifier avant de voter.')
            await inputs.first.fill(PSEUDO)
            button = page.get_by_role('button', name='Entrer et voter')
            if await button.count() == 0:
                button = page.locator('input[type="submit"][value*="voter" i]')
            if await button.count() != 1:
                raise RuntimeError('Bouton de vote non trouvé de manière fiable.')
            await button.first.click(timeout=15000)
            await page.wait_for_load_state('domcontentloaded', timeout=20000)
            await page.screenshot(path='apres.png', full_page=True)
            print('URL après clic :', page.url)
            print('Extrait du résultat :', (await page.locator('body').inner_text())[:1600])
            print('IMPORTANT : le script a soumis le formulaire, mais ne peut pas confirmer à lui seul que le vote a été comptabilisé.')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
