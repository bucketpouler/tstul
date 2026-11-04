
import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

# CONFIGURATION
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
    """Sauvegarde la capture et le texte de la page."""

    base = DOSSIER / f"{nom}-{etape}"

    if page.is_closed():
        print("Impossible de capturer : page fermée.")
        return False

    await page.screenshot(
        path=str(base) + ".png",
        full_page=True,
        timeout=15000
    )

    texte = await page.locator("body").inner_text()

    Path(str(base) + ".txt").write_text(
        f"URL : {page.url}\n\n{texte}",
        encoding="utf-8"
    )

    print("CAPTURE :", str(base) + ".png")
    print("URL :", page.url)
    print("CONTENU :", texte[:1500].replace("\n", " "))

    return True


async def ouvrir_formulaire(page):
    """Ouvre le formulaire et identifie sa fenêtre."""

    refus = page.get_by_text(
        re.compile(r"Ce vote n.est pas comptabilis", re.I)
    )

    if await refus.count() == 0:
        print("Aucun message de refus initial.")
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

        print("Nouvelle fenêtre détectée :", nouvelle_page.url)

        return nouvelle_page

    print("Pas de nouvelle fenêtre détectée.")
    return page


async def trouver_resultat(page, pages_avant):
    """Repère une éventuelle nouvelle fenêtre après validation."""

    await asyncio.sleep(2)

    nouvelles_pages = [
        p for p in page.context.pages
        if p not in pages_avant and not p.is_closed()
    ]

    if nouvelles_pages:
        resultat = nouvelles_pages[-1]

        try:
            await resultat.wait_for_load_state(
                "domcontentloaded",
                timeout=15000
            )
        except Exception:
            pass

        print("Fenêtre de résultat détectée :", resultat.url)
        return resultat

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

        # 1. Accéder au formulaire.
        page_formulaire = await ouvrir_formulaire(page)

        await sauvegarder(
            page_formulaire,
            nom,
            "formulaire"
        )

        # 2. Identifier le champ du votant.
        champs = page_formulaire.locator(
            'input[type="text"], input:not([type])'
        )

        nombre = await champs.count()

        if nombre != 1:
            print(
                f"ÉCHEC : {nombre} champ(s) texte trouvé(s)."
            )
            return

        # 3. Remplir Tulipe.
        await champs.first.fill(PSEUDO)

        valeur = await champs.first.input_value()

        if valeur != PSEUDO:
            print("ÉCHEC : pseudo incorrect.")
            return

        print("Identifiant du votant vérifié :", valeur)

        await sauvegarder(
            page_formulaire,
            nom,
            "pseudo-rempli"
        )

        # 4. Identifier le bouton de vote.
        bouton = page_formulaire.locator(
            'input[type="image"]'
        )

        nombre_boutons = await bouton.count()

        if nombre_boutons != 1:
            print(
                f"ÉCHEC : {nombre_boutons} bouton(s) image."
            )
            return

        # Vérifier qu'il appartient au formulaire.
        meme_formulaire = await bouton.first.evaluate("""
            bouton => {
                const champ = document.querySelector(
                    'input[type="text"], input:not([type])'
                );

                return !!(
                    champ &&
                    bouton.form &&
                    bouton.form === champ.form
                );
            }
        """)

        if not meme_formulaire:
            print(
                "ÉCHEC : bouton non associé "
                "au formulaire de vote."
            )
            return

        # 5. Cliquer pour valider le vote.
        print("VALIDATION DU VOTE...")

        pages_avant = set(page_formulaire.context.pages)

        try:
            await bouton.first.click(
                timeout=15000,
                no_wait_after=True
            )

            print("Clic sur le bouton effectué.")

        except Exception as exc:
            print(
                "Erreur pendant le clic :",
                type(exc).__name__,
                str(exc)[:300]
            )

            # Ne pas recliquer : la soumission
            # a peut-être déjà été effectuée.

        # 6. Identifier la page après validation.
        page_resultat = await trouver_resultat(
            page_formulaire,
            pages_avant
        )

        try:
            await page_resultat.wait_for_load_state(
                "domcontentloaded",
                timeout=10000
            )
        except Exception:
            pass

        # 7. CAPTURE APRÈS VALIDATION.
        capture_ok = await sauvegarder(
            page_resultat,
            nom,
            "resultat-apres-validation"
        )

        if not capture_ok:
            print(
                "ATTENTION : résultat non capturé."
            )
            return

        # 8. Analyser le résultat.
        texte = (
            await page_resultat.locator("body").inner_text()
        ).lower()

        if "ce vote n'est pas comptabilisé" in texte:
            print(
                "RÉSULTAT : VOTE NON COMPTABILISÉ"
            )

        elif "vote comptabilisé" in texte:
            print(
                "RÉSULTAT : confirmation de vote détectée."
            )

        else:
            print(
                "RÉSULTAT : soumission effectuée, "
                "confirmation à vérifier dans la capture."
            )

    except Exception as exc:
        print(
            f"ERREUR : {type(exc).__name__} : {exc}"
        )

        try:
            if not page_formulaire.is_closed():
                await sauvegarder(
                    page_formulaire,
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
