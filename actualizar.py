"""Lee la tasa oficial (dólar y euro) de la página del BCV y la guarda en tasa.json."""
import json, os, re, sys, time
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.bcv.org.ve/"
ARCHIVO = "tasa.json"
NUM = r"(\d{1,3}(?:\.\d{3})*,\d{2,10}|\d+,\d{2,10}|\d+\.\d{2,10})"
MESES = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05",
         "junio": "06", "julio": "07", "agosto": "08", "septiembre": "09",
         "setiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}


def a_numero(t):
    t = t.strip().replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t)


def sacar_monto(html, texto, moneda, bloque):
    # 1) por el bloque con id (formato clásico de la web)
    m = re.search(r'id=["\']%s["\'].*?<strong>\s*%s\s*</strong>' % (bloque, NUM), html, re.S | re.I)
    if m:
        return a_numero(m.group(1))
    # 2) por el texto visible: "USD 871,36890000"
    m = re.search(r"\b%s\b\s*:?\s*%s" % (moneda, NUM), texto, re.I)
    return a_numero(m.group(1)) if m else None


def sacar_fecha(html, texto):
    m = re.search(r'content="(\d{4}-\d{2}-\d{2})T', html)
    if m:
        return m.group(1)
    m = re.search(r"(\d{1,2})\s+(?:de\s+)?([A-Za-záéíóú]+)\s+(?:de\s+)?(\d{4})", texto)
    if m and m.group(2).lower() in MESES:
        return "%s-%s-%s" % (m.group(3), MESES[m.group(2).lower()], m.group(1).zfill(2))
    return None


def parsear(html):
    sin_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", sin_script))
    return {
        "usd": sacar_monto(html, texto, "USD", "dolar"),
        "eur": sacar_monto(html, texto, "EUR", "euro"),
        "fecha_valor": sacar_fecha(html, texto),
    }, texto


def descargar():
    cab = {"User-Agent": "Mozilla/5.0 (compatible; TasaBot/1.0)"}
    error = None
    for _ in range(3):
        for verificar in (True, False):
            try:
                r = requests.get(URL, headers=cab, timeout=30, verify=verificar)
                r.raise_for_status()
                return r.text
            except Exception as e:  # noqa: BLE001
                error = e
        time.sleep(5)
    raise RuntimeError("No se pudo abrir la página del BCV: %s" % error)


def main():
    html = descargar()
    nuevo, texto = parsear(html)
    if not (nuevo["usd"] and nuevo["eur"] and nuevo["fecha_valor"]):
        print("No pude leer los datos:", nuevo, "| tamaño de la página:", len(html))
        for palabra in ("USD", "EUR", "dolar", "euro"):
            for m in list(re.finditer(palabra, html))[:2]:
                print("--- HTML cerca de", palabra, ":", html[max(0, m.start() - 150): m.start() + 350].replace("\n", " "))
        print("--- TEXTO cerca de USD:", texto[max(0, texto.find("USD") - 100): texto.find("USD") + 200])
        sys.exit(1)

    anterior = {}
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, encoding="utf-8") as f:
            anterior = json.load(f)
    if anterior.get("usd") and not 0.9 <= nuevo["usd"] / anterior["usd"] <= 1.3:
        print("Valor sospechoso, no se guarda:", nuevo, "anterior:", anterior)
        sys.exit(1)
    if all(anterior.get(k) == nuevo[k] for k in ("usd", "eur", "fecha_valor")):
        print("Sin cambios:", nuevo)
        return
    nuevo["actualizado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(nuevo, f, ensure_ascii=False, indent=2)
    print("Guardado:", nuevo)


if __name__ == "__main__":
    main()
