#!/usr/bin/env python3
"""Meldet, wenn sich das BMF-Bewerbungsfenster für Pflichtpraktika ändert."""
import os, pathlib, re, sys
import requests
from bs4 import BeautifulSoup

URL = ("https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/"
       "Ministerium/Arbeiten-Ausbildung/praktikum.html")
NTFY_URL = os.environ["NTFY_URL"]
STATE = pathlib.Path("state/bmf.txt")

MONATE = ("Januar|Februar|März|April|Mai|Juni|"
          "Juli|August|September|Oktober|November|Dezember")

SATZ = re.compile(r"aktuell\s+Bewerbungen.{0,200}?beginnen\.", re.IGNORECASE)
DATUM = re.compile(rf"\d{{1,2}}\.\s*(?:{MONATE})\s*\d{{4}}")

def notify(titel: str, text: str) -> None:
    r = requests.post(NTFY_URL, data=text.encode("utf-8"),
                      headers={"Title": titel, "Priority": "high",
                               "Tags": "briefcase", "Click": URL}, timeout=15)
    r.raise_for_status()
    print(f"ntfy-Antwort: {r.status_code} – {r.text[:200]}")


def fetch_fenster() -> str:
    r = requests.get(URL, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (compatible; bmf-praktikum-watcher/1.0)",
        "Accept-Language": "de-DE,de;q=0.9",
    })
    r.raise_for_status()

    text = " ".join(BeautifulSoup(r.text, "html.parser")
                    .get_text(separator=" ").split())

    satz = SATZ.search(text)
    if satz is None:
        notify("BMF-Watcher: Satz nicht gefunden",
               "Die Formulierung zum Bewerbungsfenster wurde nicht erkannt. "
               "Bitte die Seite manuell prüfen und den Regex anpassen.")
        sys.exit("Muster nicht gefunden.")

    daten = DATUM.findall(satz.group(0))
    if not daten:
        notify("BMF-Watcher: keine Daten im Satz",
               f"Satz gefunden, aber ohne Datumsangabe:\n\n{satz.group(0)}")
        sys.exit("Keine Datumsangaben.")

    return " – ".join(daten)


def main() -> None:
    neu = fetch_fenster()
    alt = STATE.read_text(encoding="utf-8").strip() if STATE.exists() else None

    if alt is None:
        print(f"Erstlauf. Fenster: {neu}")
    elif alt == neu:
        print(f"Unverändert: {neu}")
        return
    else:
        print(f"ÄNDERUNG: {alt}  ->  {neu}")
        notify("BMF-Praktikum: neuer Bewerbungszeitraum!",
               f"Bisher: {alt}\nJetzt:  {neu}")

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(neu, encoding="utf-8")


if __name__ == "__main__":
    main()
