
"""Test des formulaires Root-Top et diagnostic des votes refusés."""

import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

PSEUDO = "Tulipe"

SITES = {
    "justmarried-1333": "http://www.root-top.com/topsite/justmarried/in.php?IDmark=1333",
    "virtu4ldreaiviz-5970": "http://www.root-top.com/topsite/virtu4ldreaiviz/in.php?IDmark=5970",
    "virtu4lgames-7046": "http://www.root-top.com/topsite/virtu4lgames/in.php?IDmark=7046",
    "gilgamesh-8765": "http://www.root-top.com/topsite/gilgamesh/in.php?IDmark=8765",
}


async def enregistrer(page, nom, etape):
    """Enregistre une capture et le texte de la page."""
    chemin = Path("captures")

    await page.screenshot(
        path=str(chemin / f"{nom}-{etape}.png"),
        full_page=True
    )

    texte = await page.locator("body").inner_text()

    (chemin / f"{nom}-{etape}.txt").write_text(
        f"URL : {page.url}\n\n{texte}",
        encoding="utf-8"
    )

    print(f"URL : {page.url}")
    print(f"Texte : {texte[:1500].replace(chr(10), ' ')}")


async def attendre_page(page):
    """Laisse la navigation se terminer."""
    try:
        await page.wait_for_load_state(
            "domcontentloaded",
            timeout=15000
        )
    except Exception:
        pass

    await page.wait_for_timeout(1500)


async def diagnostiquer_refus(page, nom):
    """Ouvre la page explicative d'un vote non comptabilisé."""

    lien = page.get_by_text(
        re.compile(
            r"Ce vote n.est pas comptabilis",
            re.IGNORECASE
        )
    )

    if await lien.count() == 0:
        print("Aucun lien de refus détecté.")
        return False

    print("VOTE NON COMPTABILISÉ")
    print("Ouverture des détails du refus...")

    try:
        await lien.first.click(timeout=15000)
        await attendre_page(page)

        await enregistrer(
            page,
            nom,
            "details-refus"
        )

        print("Diagnostic du refus enregistré.")
        return True

    except Exception as exc:
        print(
            f"Impossible d'ouvrir les détails : "
            f"{type(exc).__name__} : {exc}"
        )

        await enregistrer(
            page,
            nom,
            "erreur-diagnostic"
        )

        return False


async def tester(page, nom, url):

    print(f"\n===== {nom} =====")

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        print(
            "HTTP initial :",
            response.status if response else "sans réponse"
        )

        await enregistrer(page, nom, "avant")

        candidates = page.locator(
            'input[type="text"], input:not([type])'
        )

        nb = await candidates.count()

        if nb != 1:
            print(
                f"NON SOUMIS : {nb} champs texte trouvés."
            )
            return

        await candidates.first.fill(PSEUDO)

        bouton = page.get_by_role(
            "button",
            name=re.compile(
                "entrer et voter",
                re.IGNORECASE
            )
        )

        if await bouton.count() != 1:
            bouton = page.locator(
                'input[type="submit"][value*="voter" i]'
            )

        if await bouton.count() != 1:
            print(
                "NON SOUMIS : bouton introuvable."
            )
            return

        print(f"Soumission du vote : {PSEUDO}")

        await bouton.first.click(timeout=15000)

        await attendre_page(page)

        await enregistrer(page, nom, "apres")

        refus = await diagnostiquer_refus(
            page,
            nom
        )

        if refus:
            print(
                "RÉSULTAT : vote refusé, détails enregistrés."
            )
        else:
            print(
                "RÉSULTAT : aucun message de refus détecté. "
                "Vérification manuelle nécessaire."
            )

    except Exception as exc:

        print(
            f"ÉCHEC : {type(exc).__name__} : {exc}"
        )

        try:
            await enregistrer(
                page,
                nom,
                "erreur"
            )
        except Exception:
            pass


async def main():

    Path("captures").mkdir(exist_ok=True)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        try:
            for nom, url in SITES.items():

                page = await browser.new_page(
                    locale="fr-FR"
                )

                try:
                    await tester(
                        page,
                        nom,
                        url
                    )
                finally:
                    await page.close()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
