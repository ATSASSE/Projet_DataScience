#!/usr/bin/env python3
"""
SCRIPT 1 — Conversion Excel Teltonika → CSV RMS + Import automatique via API
=============================================================================
1. Sélectionne le fichier Excel Teltonika (fenêtre)
2. Entre le numéro de départ T000X
3. Génère le CSV
4. Envoie automatiquement tous les RUT dans ton espace RMS via l'API
"""

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import pandas as pd
import requests
import json
import time
from pathlib import Path

RMS_API_BASE = "https://api.rms.teltonika-networks.com"


def format_mac(raw_mac: str) -> str:
    mac = str(raw_mac).strip().upper().replace(":", "").replace("-", "")
    if len(mac) != 12:
        raise ValueError(f"MAC invalide : '{raw_mac}'")
    return ":".join(mac[i:i+2] for i in range(0, 12, 2))


def parse_start_number(start: str):
    prefix = ''.join(filter(str.isalpha, start))
    number = ''.join(filter(str.isdigit, start))
    if not number:
        return None, None
    return prefix or "T", int(number)


def rms_get_companies(token: str) -> list:
    """Récupère la liste des companies RMS de l'utilisateur."""
    resp = requests.get(
        f"{RMS_API_BASE}/companies",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15
    )
    print(f"   [DEBUG companies] Status: {resp.status_code} | Réponse: {resp.text[:500]}")
    if resp.status_code == 200:
        data = resp.json()
        return data.get("data", [])
    return []


def rms_add_device(token: str, company_id: int, name: str, serial: str,
                   mac: str, password: str) -> dict:
    """Ajoute un seul RUT dans RMS via l'API."""
    payload = {
        "data": [
            {
                "company_id":            int(company_id),
                "device_series":         "rut",
                "auto_credit_enable":    True,
                "serial":                serial,
                "mac":                   mac,
                "name":                  name,
                "password":              password,
                "password_confirmation": password
            }
        ]
    }
    print(f"      [DEBUG payload] {payload}")
    resp = requests.post(
        f"{RMS_API_BASE}/devices",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json"
        },
        json=payload,
        timeout=20
    )
    # Affiche la réponse complète pour debug
    print(f"      [DEBUG] Status: {resp.status_code} | Réponse: {resp.text[:300]}")
    return {"status_code": resp.status_code, "body": resp.text}


def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print()
    print("=" * 60)
    print("   Conversion Excel Teltonika  →  CSV RMS + Import Auto")
    print("=" * 60)
    print()

    # ── Étape 1 : Sélection du fichier Excel ──────────────────────────────────
    print("   📂 Étape 1 — Sélectionne ton fichier Excel Teltonika...")
    excel_path_str = filedialog.askopenfilename(
        title="Étape 1 — Sélectionne le fichier Excel Teltonika",
        filetypes=[("Fichiers Excel", "*.xlsx *.xls"), ("Tous les fichiers", "*.*")]
    )
    if not excel_path_str:
        print("   ❌ Aucun fichier sélectionné. Arrêt.")
        sys.exit(0)
    excel_path = Path(excel_path_str)
    print(f"   ✅ Fichier : {excel_path.name}")
    print()

    # ── Étape 2 : Numéro de départ ────────────────────────────────────────────
    while True:
        start_input = simpledialog.askstring(
            title="Étape 2 — Numéro de départ",
            prompt="Numéro de départ pour les RUT ?\n(Appuie sur OK pour garder T0001)",
            initialvalue="T0001"
        )
        if start_input is None:
            start_input = "T0001"
        prefix, start_num = parse_start_number(start_input.strip())
        if start_num is not None:
            break
        messagebox.showwarning("Format invalide", f"'{start_input}' n'est pas valide.\nExemple : T0001")
    print(f"   🔢 Numéro de départ : {start_input.strip()}")
    print()

    # ── Étape 3 : Token API RMS ───────────────────────────────────────────────
    token_input = simpledialog.askstring(
        title="Étape 3 — Token API RMS",
        prompt=(
            "Entre ton Personal Access Token RMS :\n\n"
            "Pour le créer :\n"
            "  1. rms.teltonika-networks.com\n"
            "  2. Profil → Account Settings → Security\n"
            "  3. Personal Access Tokens → Create Token\n\n"
            "(Laisse vide pour générer le CSV sans importer dans RMS)"
        )
    )
    rms_token = (token_input or "").strip()
    import_to_rms = bool(rms_token)

    # ── Chargement Excel ──────────────────────────────────────────────────────
    print(f"   Lecture de : {excel_path.name} ...")
    try:
        df = pd.read_excel(excel_path, header=1)
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de lire le fichier Excel :\n{e}")
        sys.exit(1)

    required = ["S/N", "MAC", "DevicePassword"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        messagebox.showerror("Erreur", f"Colonnes manquantes : {missing}")
        sys.exit(1)

    df = df.dropna(subset=["S/N", "MAC", "DevicePassword"]).reset_index(drop=True)
    total = len(df)
    print(f"   {total} RUT détectés dans le fichier")

    names = [f"{prefix}{str(start_num + i).zfill(4)}" for i in range(total)]

    rows = []
    for i, row in df.iterrows():
        try:
            mac_fmt = format_mac(row["MAC"])
        except ValueError:
            mac_fmt = str(row["MAC"])
        rows.append({
            "mac":                   mac_fmt,
            "serial":                str(int(row["S/N"])),
            "name":                  names[i],
            "password_confirmation": str(row["DevicePassword"]).strip()
        })

    result_df = pd.DataFrame(rows, columns=["mac", "serial", "name", "password_confirmation"])

    # ── Étape 4 : Sauvegarder le CSV ─────────────────────────────────────────
    print()
    print("   💾 Étape 4 — Choisis où sauvegarder le CSV...")
    default_name = f"rms_import_{names[0]}-{names[-1]}.csv"
    output_path_str = filedialog.asksaveasfilename(
        title="Étape 4 — Enregistrer le CSV généré",
        initialdir=excel_path.parent,
        initialfile=default_name,
        defaultextension=".csv",
        filetypes=[("Fichier CSV", "*.csv"), ("Tous les fichiers", "*.*")]
    )
    if not output_path_str:
        print("   ❌ Sauvegarde annulée. Arrêt.")
        sys.exit(0)

    output_path = Path(output_path_str)
    result_df.to_csv(output_path, index=False)
    print(f"   ✅ CSV sauvegardé : {output_path.name}")

    # ── Étape 5 : Import automatique dans RMS ─────────────────────────────────
    if not import_to_rms:
        print()
        print("   ⚠️  Pas de token RMS fourni — import ignoré.")
        messagebox.showinfo("✅ CSV généré",
            f"CSV généré !\n\n"
            f"Fichier : {output_path.name}\n"
            f"Dossier : {output_path.parent}\n\n"
            f"{total} RUT : {names[0]} → {names[-1]}\n\n"
            f"(Import RMS ignoré — pas de token)"
        )
        return

    print()
    print("   🌐 Étape 5 — Connexion à l'API RMS...")

    # Récupération des companies
    companies = rms_get_companies(rms_token)
    if not companies:
        messagebox.showerror("Erreur API RMS",
            "Impossible de se connecter à RMS.\n"
            "Vérifie ton token et ta connexion internet."
        )
        sys.exit(1)

    # Sélection de la company si plusieurs
    if len(companies) == 1:
        company_id   = companies[0]["id"]
        company_name = companies[0].get("name", str(company_id))
        print(f"   Company RMS : {company_name}")
    else:
        company_names = [f"{c.get('name', '?')} (ID: {c['id']})" for c in companies]
        choice = simpledialog.askstring(
            title="Choix de la Company RMS",
            prompt="Plusieurs companies trouvées. Entre le numéro :\n\n" +
                   "\n".join(f"{i+1}. {n}" for i, n in enumerate(company_names))
        )
        try:
            idx = int(choice) - 1
            company_id   = companies[idx]["id"]
            company_name = companies[idx].get("name", str(company_id))
        except Exception:
            messagebox.showerror("Erreur", "Choix invalide. Arrêt.")
            sys.exit(1)

    print(f"   🚀 Import de {total} RUT dans RMS ({company_name})...\n")

    success_count = 0
    failed = []

    for i, row in enumerate(rows):
        name     = row["name"]
        serial   = row["serial"]
        mac      = row["mac"]
        password = row["password_confirmation"]

        result = rms_add_device(rms_token, company_id, name, serial, mac, password)
        code = result["status_code"]

        if code in (200, 201):
            success_count += 1
            print(f"   ✅ [{i+1:3}/{total}] {name} — OK")
        elif code == 422:
            failed.append({"name": name, "serial": serial, "raison": "Déjà existant ou données invalides"})
            print(f"   ⚠️  [{i+1:3}/{total}] {name} — Déjà dans RMS ou données invalides")
        elif code == 429:
            print(f"   ⏳ Rate limit RMS atteint — attente 5s...")
            time.sleep(5)
            # Retry
            result2 = rms_add_device(rms_token, company_id, name, serial, mac, password)
            if result2["status_code"] in (200, 201):
                success_count += 1
                print(f"   ✅ [{i+1:3}/{total}] {name} — OK (retry)")
            else:
                failed.append({"name": name, "serial": serial, "raison": f"Erreur {result2['status_code']}"})
                print(f"   ❌ [{i+1:3}/{total}] {name} — Échec (code {result2['status_code']})")
        else:
            failed.append({"name": name, "serial": serial, "raison": f"Erreur HTTP {code}"})
            print(f"   ❌ [{i+1:3}/{total}] {name} — Échec (code {code})")

        # Petite pause pour ne pas saturer l'API
        time.sleep(0.3)

    # ── Rapport final ─────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"   ✅ Terminé !")
    print(f"   CSV      : {output_path.name}")
    print(f"   Importés : {success_count}/{total} dans RMS")
    if failed:
        print(f"   Échecs   : {len(failed)}")
        for f in failed:
            print(f"     - {f['name']} (SN:{f['serial']}) → {f['raison']}")
    print("=" * 60)
    print()

    msg = (
        f"Import terminé !\n\n"
        f"✅ {success_count}/{total} RUT importés dans RMS\n"
        f"📄 CSV sauvegardé : {output_path.name}\n"
    )
    if failed:
        msg += f"\n⚠️ {len(failed)} échec(s) :\n"
        msg += "\n".join(f"  - {f['name']} : {f['raison']}" for f in failed)

    messagebox.showinfo("✅ Import RMS terminé", msg)


if __name__ == "__main__":
    main()
