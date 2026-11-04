
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

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
    """Sauvegarde une capture et le texte affiché."""
    base = DOSSIER / f"{nom}-{etape}"

    await page.screenshot(
        path=str(base) + ".png",
        full_page=True
    )

    texte = await page.locator("body").inner_text()

    Path(str(base) + ".txt").write_text(
        f"URL : {page.url}\n\n{texte}",
        encoding="utf-8"
    )

    print("URL :", page.url)
    print("CONTENU :", texte[:1500].replace("\n", " "))


async def ouvrir_formulaire(page, nom):
    """Ouvre le formulaire et récupère la bonne fenêtre."""

    refus = page.get_by_text(
        re.compile(r"Ce vote n.est pas comptabilis", re.I)
    )

    if await refus.count() == 0:
        print("Aucun message de refus initial.")
        return page

    print("Ouverture du formulaire...")

    pages_avant = set(page.context.pages)

    await refus.first.click(timeout=15000)

    # Laisser le temps à une éventuelle nouvelle fenêtre.
    await page.wait_for_timeout(1500)

    nouvelles_pages = [
        p for p in page.context.pages
        if p not in pages_avant
    ]

    if nouvelles_pages:
        nouvelle_page = nouvelles_pages[-1]

        await nouvelle_page.wait_for_load_state(
            "domcontentloaded",
            timeout=15000
        )

        print("Nouvelle fenêtre détectée :", nouvelle_page.url)
        return nouvelle_page

    # Vérifier si le formulaire est apparu dans la même page.
    champs = page.locator(
        'input[type="text"], input:not([type])'
    )

    if await champs.count() > 0:
        print("Formulaire trouvé dans la même fenêtre.")
        return page

    print("Formulaire non détecté après le clic.")
    return page


async def tester(page, nom, url):
    print(f"\n===== {nom} =====")

    page_formulaire = page

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        print("HTTP :", response.status if response else "?")

        await sauvegarder(page, nom, "avant")

        # Ouvrir le formulaire et récupérer la fenêtre active.
        page_formulaire = await ouvrir_formulaire(page, nom)

        await sauvegarder(
            page_formulaire,
            nom,
            "formulaire"
        )

        champs = page_formulaire.locator(
            'input[type="text"], input:not([type])'
        )

        if await champs.count() != 1:
            print(
                "ÉCHEC : champ du pseudo introuvable. "
                f"Nombre de champs : {await champs.count()}"
            )
            return

        # Renseigner le pseudo.
        await champs.first.fill(PSEUDO)

        print("Pseudo renseigné :", PSEUDO)

        bouton = page_formulaire.get_by_role(
            "button",
            name=re.compile("entrer et voter", re.I)
        )

        if await bouton.count() != 1:
            bouton = page_formulaire.locator(
                'input[type="submit"][value*="voter" i]'
            )

        if await bouton.count() != 1:
            print("ÉCHEC : bouton de vote introuvable.")
            return

        print("Envoi du vote...")

        # Une seule soumission par topsite.
        await bouton.first.click(timeout=15000)

        try:
            await page_formulaire.wait_for_load_state(
                "domcontentloaded",
                timeout=15000
            )
        except PlaywrightTimeout:
            print("Navigation non confirmée.")

        await page_formulaire.wait_for_timeout(1500)

        await sauvegarder(
            page_formulaire,
            nom,
            "resultat"
        )

        texte = (
            await page_formulaire.locator("body").inner_text()
        ).lower()

        if "ce vote n'est pas comptabilisé" in texte:
            print("RÉSULTAT : VOTE NON COMPTABILISÉ")
        else:
            print(
                "RÉSULTAT : soumission effectuée. "
                "Vérification de la confirmation nécessaire."
            )

    except Exception as exc:
        print(
            f"ERREUR : {type(exc).__name__} : {exc}"
        )

        try:
            await sauvegarder(
                page_formulaire,
                nom,
                "erreur"
            )
        except Exception:
            pass


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            for nom, url in SITES.items():
                page = await browser.new_page(
                    locale="fr-FR"
                )

                try:
                    await tester(page, nom, url)
                finally:
                    await page.context.close()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
