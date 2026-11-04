
import asyncio
import json
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
DOSSIER.mkdir(parents=True, exist_ok=True)


async def sauvegarder(page, nom, etape):
    """Enregistre la capture et le texte de la page."""

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
    print(
        "CONTENU :",
        texte[:1500].replace("\n", " ")
    )


async def ouvrir_formulaire(page):
    """Récupère la fenêtre contenant le formulaire."""

    refus = page.get_by_text(
        re.compile(
            r"Ce vote n.est pas comptabilis",
            re.I
        )
    )

    if await refus.count() == 0:
        print("Aucun message initial de refus.")
        return page

    print("Ouverture du formulaire...")

    pages_avant = set(page.context.pages)

    await refus.first.click(timeout=15000)

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

        print(
            "Nouvelle fenêtre détectée :",
            nouvelle_page.url
        )

        return nouvelle_page

    champs = page.locator(
        'input[type="text"], input:not([type])'
    )

    if await champs.count() > 0:
        print("Formulaire trouvé dans la même fenêtre.")

    return page


async def analyser_boutons(page, nom):
    """Liste les éléments susceptibles de valider le formulaire."""

    elements = await page.locator(
        'button, '
        'input[type="submit"], '
        'input[type="image"], '
        'a, '
        '[role="button"]'
    ).evaluate_all("""
        elements => elements.map(el => ({
            tag: el.tagName,
            type: el.getAttribute("type"),
            texte: (el.innerText || "").trim(),
            valeur: el.getAttribute("value"),
            titre: el.getAttribute("title"),
            alt: el.getAttribute("alt"),
            href: el.getAttribute("href")
        }))
    """)

    print(
        "ÉLÉMENTS CLIQUABLES :",
        json.dumps(
            elements,
            ensure_ascii=False,
            indent=2
        )
    )

    chemin = DOSSIER / f"{nom}-boutons.json"

    chemin.write_text(
        json.dumps(
            elements,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("Diagnostic enregistré :", chemin)


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

        page_formulaire = await ouvrir_formulaire(page)

        await sauvegarder(
            page_formulaire,
            nom,
            "formulaire"
        )

        champs = page_formulaire.locator(
            'input[type="text"], input:not([type])'
        )

        nombre = await champs.count()

        if nombre != 1:
            print(
                "ÉCHEC : champ du pseudo introuvable. "
                f"Nombre de champs : {nombre}"
            )
            return

        await champs.first.fill(PSEUDO)

        print("Pseudo renseigné :", PSEUDO)

        await sauvegarder(
            page_formulaire,
            nom,
            "pseudo-rempli"
        )

        await analyser_boutons(
            page_formulaire,
            nom
        )

        print(
            "DIAGNOSTIC TERMINÉ : "
            "aucun vote soumis pendant ce test."
        )

    except Exception as exc:
        print(
            f"ERREUR : {type(exc).__name__} : {exc}"
        )

        try:
            await sauvegarder(
                page,
                nom,
                "erreur"
            )
        except Exception:
            pass


async def main():

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
                    await page.context.close()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
