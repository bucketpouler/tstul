
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

DOSSIER = Path("captures")
DOSSIER.mkdir(exist_ok=True)


async def sauvegarder(page, nom, etape):
    fichier = DOSSIER / f"{nom}-{etape}"

    await page.screenshot(
        path=str(fichier.with_suffix(".png")),
        full_page=True
    )

    texte = await page.locator("body").inner_text()

    fichier.with_suffix(".txt").write_text(
        f"URL : {page.url}\n\n{texte}",
        encoding="utf-8"
    )

    print(f"URL : {page.url}")
    print("CONTENU :", texte[:2000].replace("\n", " "))


async def diagnostic(page, nom):
    """Consulte les détails d'un refus déjà affiché."""

    message = page.get_by_text(
        re.compile(
            r"Ce vote n.est pas comptabilis",
            re.IGNORECASE
        )
    )

    if await message.count() == 0:
        return False

    print("REFUS DÉTECTÉ : vote non comptabilisé")

    await sauvegarder(page, nom, "refus")

    try:
        print("Ouverture des détails...")

        async with page.context.expect_page(
            timeout=3000
        ) as nouvelle_page_info:
            await message.first.click(timeout=10000)

        details = await nouvelle_page_info.value
        await details.wait_for_load_state(
            "domcontentloaded",
            timeout=15000
        )

        await sauvegarder(
            details, nom, "details-refus"
        )

        await details.close()

    except Exception as exc:
        print("Pas de nouvelle fenêtre :", str(exc)[:200])

        try:
            await page.wait_for_load_state(
                "domcontentloaded",
                timeout=10000
            )
        except Exception:
            pass

        await sauvegarder(
            page, nom, "details-refus"
        )

    return True


async def tester(page, nom, url):
    print(f"\n===== {nom} =====")

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        print(
            "HTTP :",
            response.status if response else "?"
        )

        await sauvegarder(page, nom, "avant")

        # Vérifier le refus AVANT le formulaire.
        if await diagnostic(page, nom):
            print("FIN : diagnostic effectué, aucun vote soumis.")
            return

        champs = page.locator(
            'input[type="text"], input:not([type])'
        )

        if await champs.count() != 1:
            print("Formulaire absent : aucun vote soumis.")
            return

        await champs.first.fill(PSEUDO)

        bouton = page.get_by_role(
            "button",
            name=re.compile("entrer et voter", re.I)
        )

        if await bouton.count() != 1:
            bouton = page.locator(
                'input[type="submit"][value*="voter" i]'
            )

        if await bouton.count() != 1:
            print("Bouton de vote introuvable.")
            return

        print("Formulaire trouvé : vote avec Tulipe")

        await bouton.first.click(timeout=15000)

        try:
            await page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000
            )
        except Exception:
            pass

        await sauvegarder(page, nom, "apres")

        if not await diagnostic(page, nom):
            print("Résultat à vérifier dans les captures.")

    except Exception as exc:
        print(f"ERREUR : {type(exc).__name__} : {exc}")

        try:
            await sauvegarder(page, nom, "erreur")
        except Exception:
            pass


async def main():
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
