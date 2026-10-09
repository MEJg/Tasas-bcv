"""Lee la tasa oficial (dólar y euro) de la página del BCV y la guarda en tasa.json.
Solo reescribe el archivo si algo cambió, para no llenar el repositorio de commits."""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.bcv.org.ve/"
ARCHIVO = "tasa.json"
MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05",
    "junio": "06", "julio": "07", "agosto": "08", "septiembre": "09",
    "setiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}


def a_numero(texto):
    t = texto.strip().replace(" ", "")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    return float(t)


def sacar_monto(html, bloque):
    m = re.search(
        r'id="%s".*?<strong>\s*([\d.,]+)\s*</strong>' % bloque, html, re.S | re.I
    )
    return a_numero(m.group(1)) if m else None


def sacar_fecha(html):
    m = re.search(
        r'date-display-single"[^>]*content="(\d{4}-\d{2}-\d{2})', html, re.I
    )
    if m:
        return m.group(1)
    m = re.search(
        r"date-display-single[^>]*>[^<]*?(\d{1,2})\s+([A-Za-záéíóú]+)\s+(\d{4})",
        html,
        re.I,
    )
    if m and m.group(2).lower() in MESES:
        return "%s-%s-%s" % (m.group(3), MESES[m.group(2).lower()], m.group(1).zfill(2))
    return None


def parsear(html):
    return {
        "usd": sacar_monto(html, "dolar"),
        "eur": sacar_monto(html, "euro"),
        "fecha_valor": sacar_fecha(html),
    }


def descargar():
    cabeceras = {"User-Agent": "Mozilla/5.0 (compatible; TasaBot/1.0)"}
    ultimo_error = None
    for intento in range(3):
        for verificar in (True, False):  # la web del BCV a veces tiene el certificado vencido
            try:
                r = requests.get(URL, headers=cabeceras, timeout=30, verify=verificar)
                r.raise_for_status()
                return r.text
            except Exception as e:  # noqa: BLE001
                ultimo_error = e
        time.sleep(5)
    raise RuntimeError("No se pudo abrir la página del BCV: %s" % ultimo_error)


def main():
    nuevo = parsear(descargar())
    if not (nuevo["usd"] and nuevo["eur"] and nuevo["fecha_valor"]):
        print("No pude leer los datos de la página (cambió el diseño?):", nuevo)
        sys.exit(1)

    anterior = {}
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, encoding="utf-8") as f:
            anterior = json.load(f)

    # Freno de seguridad: si el valor se mueve de forma absurda, no lo guardamos.
    if anterior.get("usd"):
        razon = nuevo["usd"] / anterior["usd"]
        if not 0.9 <= razon <= 1.3:
            print("Valor sospechoso, no se guarda:", nuevo, "anterior:", anterior)
            sys.exit(1)

    if (
        anterior.get("usd") == nuevo["usd"]
        and anterior.get("eur") == nuevo["eur"]
        and anterior.get("fecha_valor") == nuevo["fecha_valor"]
    ):
        print("Sin cambios:", nuevo)
        return

    nuevo["actualizado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(nuevo, f, ensure_ascii=False, indent=2)
    print("Guardado:", nuevo)


if __name__ == "__main__":
    main()
