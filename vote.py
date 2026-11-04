
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
    """Enregistre la capture et le texte de la page."""
    fichier = DOSSIER / f"{nom}-{etape}"

    await page.screenshot(
        path=str(fichier) + ".png",
        full_page=True
    )

    texte = await page.locator("body").inner_text()

    (Path(str(fichier) + ".txt")).write_text(
        f"URL : {page.url}\n\n{texte}",
        encoding="utf-8"
    )

    print(f"URL : {page.url}")
    print("CONTENU :", texte[:1200].replace("\n", " "))


async def tester(page, nom, url):
    print(f"\n===== {nom} =====")

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        print("HTTP :", response.status if response else "?")

        await sauvegarder(page, nom, "avant")

        # Si le message apparaît, ouvrir les détails
        # pour afficher le formulaire.
        refus = page.get_by_text(
            re.compile(r"Ce vote n.est pas comptabilis", re.I)
        )

        if await refus.count() > 0:
            print("Ouverture du formulaire...")
            await refus.first.click(timeout=10000)
            await page.wait_for_timeout(1000)

        await sauvegarder(page, nom, "formulaire")

        # Rechercher le champ du pseudo.
        champs = page.locator(
            'input[type="text"], input:not([type])'
        )

        if await champs.count() != 1:
            print("ÉCHEC : champ du pseudo introuvable.")
            return

        # Remplir le pseudo Tulipe.
        await champs.first.fill(PSEUDO)

        print(f"Pseudo renseigné : {PSEUDO}")

        # Rechercher le bouton.
        bouton = page.get_by_role(
            "button",
            name=re.compile("entrer et voter", re.I)
        )

        if await bouton.count() != 1:
            bouton = page.locator(
                'input[type="submit"][value*="voter" i]'
            )

        if await bouton.count() != 1:
            print("ÉCHEC : bouton de vote introuvable.")
            return

        # Une seule soumission par topsite.
        print("Envoi du vote...")

        await bouton.first.click(timeout=15000)

        try:
            await page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000
            )
        except Exception:
            pass

        await page.wait_for_timeout(1500)

        # Sauvegarder le résultat après le vote.
        await sauvegarder(page, nom, "resultat")

        texte = (await page.locator("body").inner_text()).lower()

        if "ce vote n'est pas comptabilisé" in texte:
            print("RÉSULTAT : VOTE NON COMPTABILISÉ")
        else:
            print(
                "RÉSULTAT : soumission effectuée. "
                "Vérifier la confirmation dans la capture."
            )

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
