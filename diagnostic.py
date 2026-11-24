
import json
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CYCLE = int(os.environ.get("CYCLE", "1"))

SITES = {
    "justmarried-1333":
        "http://www.root-top.com/topsite/justmarried/in.php?IDmark=1333",
    "virtu4ldreaiviz-5970":
        "http://www.root-top.com/topsite/virtu4ldreaiviz/in.php?IDmark=5970",
    "virtu4lgames-7046":
        "http://www.root-top.com/topsite/virtu4lgames/in.php?IDmark=7046",
    "gilgamesh-8765":
        "http://www.root-top.com/topsite/gilgamesh/in.php?IDmark=8765",
}

DOSSIER = Path("rapports")
DOSSIER.mkdir(exist_ok=True)


def lire_url(url):
    requete = Request(
        url,
        headers={
            "User-Agent": "ThemisTrials-Diagnostic/1.0"
        }
    )

    try:
        with urlopen(requete, timeout=20) as response:
            contenu = response.read(500000)
            texte = contenu.decode("utf-8", errors="replace")

            return {
                "http": response.status,
                "url_finale": response.url,
                "texte": texte,
                "erreur": None
            }

    except HTTPError as e:
        return {
            "http": e.code,
            "url_finale": url,
            "texte": "",
            "erreur": str(e)
        }

    except Exception as e:
        return {
            "http": None,
            "url_finale": url,
            "texte": "",
            "erreur": str(e)
        }


def obtenir_ip():
    resultat = lire_url(
        "https://api.ipify.org?format=json"
    )

    if resultat["erreur"]:
        return None

    try:
        return json.loads(resultat["texte"])["ip"]
    except Exception:
        return None


def main():
    print(f"===== CYCLE {CYCLE}/50 =====")

    ip = obtenir_ip()
    print("IP PUBLIQUE :", ip or "indisponible")

    rapport = {
        "cycle": CYCLE,
        "ip": ip,
        "sites": {}
    }

    for nom, url in SITES.items():
        print(f"\n--- {nom} ---")

        resultat = lire_url(url)
        texte = resultat["texte"].lower()

        refus = bool(re.search(
            r"ce vote n.est pas comptabilis",
            texte
        ))

        formulaire = (
            "identifiant du votant" in texte
        )

        cookies = (
            "votre navigateur doit accepter les cookies"
            in texte
        )

        informations = {
            "http": resultat["http"],
            "url_finale": resultat["url_finale"],
            "refus_affiche": refus,
            "formulaire_visible": formulaire,
            "avertissement_cookies": cookies,
            "erreur": resultat["erreur"]
        }

        rapport["sites"][nom] = informations

        print("HTTP :", resultat["http"])
        print("Refus affiché :", refus)
        print("Formulaire visible :", formulaire)
        print("Avertissement cookies :", cookies)

        if resultat["erreur"]:
            print("ERREUR :", resultat["erreur"])

        # Pause pour limiter la charge du diagnostic.
        time.sleep(1)

    fichier = DOSSIER / f"cycle-{CYCLE:02d}.json"

    fichier.write_text(
        json.dumps(
            rapport,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\nRapport enregistré :", fichier)
    print("AUCUN VOTE SOUMIS")


if __name__ == "__main__":
    main()
