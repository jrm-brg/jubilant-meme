import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Gestion des Agapes", layout="wide")
st.title("🍽️ Gestionnaire d'Agapes (Fichiers Uniques)")

LOCAL_CSV = "Tableau de Loge - Contacts.csv"
GOOGLE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFcguChCFkKz3hLvlSmMdDgVR8WEf3XUI1DWmNGMNXL3N_qN3ErV0X3BEVpZ9xYuMPdYJn-7SBcP94/pub?gid=355758587&single=true&output=csv"

# 1. Chargement et harmonisation du fichier des contacts de base (Lecture seule)
# 1. Chargement du fichier des contacts depuis GitHub (Lecture seule et mise à jour dynamique)
URL_RAW_GITHUB = "https://raw.githubusercontent.com/jrm-brg/Agapes/main/Tableau%20de%20Loge%20-%20Contacts.csv"

try:
    # L'application va maintenant lire le fichier directement sur votre GitHub à chaque rafraîchissement
    df_contacts = pd.read_csv(URL_RAW_GITHUB)
except Exception as e:
    # Si GitHub est inaccessible, on utilise la copie locale par sécurité
    if os.path.exists(LOCAL_CSV):
        df_contacts = pd.read_csv(LOCAL_CSV)
    else:
        st.error(f"Erreur de chargement initial : {e}")
        st.stop()

df_contacts.columns = df_contacts.columns.str.strip()
rename_dict = {}
for col in df_contacts.columns:
    col_clean = col.lower().replace("é", "e").replace("û", "u").replace("°", "").replace(" ", "")
    if col_clean in ["n", "no", "id", "num", "numero"]:
        rename_dict[col] = "N°"
    elif col_clean in ["nom&prenom", "nomprenom", "identite", "membres"]:
        rename_dict[col] = "Nom & Prénom"

df_contacts = df_contacts.rename(columns=rename_dict)
if "N°" not in df_contacts.columns:
    df_contacts.insert(0, "N°", range(1, len(df_contacts) + 1))
df_contacts["N°"] = df_contacts["N°"].astype(int)

# Nettoyage cosmétique pour l'affichage
df_membres_base = df_contacts[["N°", "Nom & Prénom"]].copy()


# --- MENU LATÉRAL : SÉLECTION DE LA DATE & AJOUT VISITEURS ---

st.sidebar.header("📅 1 - Choisir la Date")
nouvelle_date = st.sidebar.date_input("Sélectionner une date :", datetime.now())
date_str = nouvelle_date.strftime("%d_%m_%Y")
date_affichage = nouvelle_date.strftime("%d/%m/%Y")

# Le nom du fichier sera unique pour cette agape
FICHIER_AGAPE = f"Agape_{date_str}.csv"

# Chargement ou création du fichier spécifique à cette date
if os.path.exists(FICHIER_AGAPE):
    df_session = pd.read_csv(FICHIER_AGAPE)
else:
    # Initialisation de la session avec les membres de la loge
    initial_rows = []
    for _, row in df_membres_base.iterrows():
        initial_rows.append({
            "N°": int(row["N°"]),
            "Nom & Prénom": row["Nom & Prénom"],
            "Présent": False,
            "Responsable": False,
            "Payé": False
        })
    df_session = pd.DataFrame(initial_rows)

df_session["N°"] = df_session["N°"].astype(int)

st.sidebar.write("---")

# Formulaire d'ajout de visiteur (Enregistré uniquement dans le fichier du jour)
st.sidebar.header("👤 2 - Ajouter un Visiteur")
st.sidebar.caption("Sera ajouté uniquement pour ce repas, sans modifier la base globale.")
with st.sidebar.form(key="visiteur_form", clear_on_submit=True):
    v_nom = st.text_input("Nom")
    v_prenom = st.text_input("Prénom")
    v_loge = st.text_input("Loge / Association")
    v_ville = st.text_input("Ville")
    submit_v = st.form_submit_button("Ajouter le visiteur ce soir")

    if submit_v:
        if v_nom and v_prenom and v_loge:
            # Génération d'un ID temporaire élevé pour les visiteurs de ce soir
            next_id = int(df_session["N°"].max() + 1) if not df_session.empty else 9000
            identite_visiteur = f"{v_nom.upper()} {v_prenom} ({v_loge} - {v_ville if v_ville else '—'})"
            
            new_v_row = {
                "N°": next_id,
                "Nom & Prénom": identite_visiteur,
                "Présent": True,       # Présent par défaut puisqu'on l'ajoute ce soir
                "Responsable": False,
                "Payé": False
            }
            df_session = pd.concat([df_session, pd.DataFrame([new_v_row])], ignore_index=True)
            df_session.to_csv(FICHIER_AGAPE, index=False)
            st.sidebar.success(f"✅ Visiteur ajouté pour le {date_affichage} !")
            st.rerun()
        else:
            st.sidebar.error("Nom, Prénom et Loge sont obligatoires.")


# --- INTERFACE PRINCIPALE À ONGLETS ---
st.header(f"🍽️ Gestion du repas du {date_affichage}")

onglet1, onglet2 = st.tabs(["👥 1. Présences & Responsables", "💶 2. Règlements (Filtré)"])

# --- ONGLET 1 : POINTAGE & RESPONSABLES ---
with onglet1:
    st.write("Cochez les personnes présentes et désignez le ou les organisateurs.")
    
    edited_presents = st.data_editor(
        df_session,
        column_config={
            "N°": st.column_config.NumberColumn(disabled=True),
            "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
            "Présent": st.column_config.CheckboxColumn("👍 Présent(e)"),
            "Responsable": st.column_config.CheckboxColumn("🍳 Responsable Agape"),
            "Payé": st.column_config.CheckboxColumn("💶 Payé", disabled=True) # Bloqué ici pour forcer l'onglet 2
        },
        disabled=["N°", "Nom & Prénom"],
        hide_index=True,
        key="editeur_presents_unique",
        use_container_width=True
    )

# --- ONGLET 2 : PAIEMENTS FILTRÉS ---
with onglet2:
    df_presents_uniquement = edited_presents[edited_presents["Présent"] == True]
    
    if df_presents_uniquement.empty:
        st.warning("⚠️ Cochez d'abord des personnes présentes dans le premier onglet pour pouvoir encaisser.")
    else:
        st.write(f"Encaisser les règlements des **{len(df_presents_uniquement)} personnes présentes** :")
        
        edited_compta = st.data_editor(
            df_presents_uniquement,
            column_config={
                "N°": st.column_config.NumberColumn(disabled=True),
                "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                "Présent": None, # Cache la colonne présent devenue inutile ici
                "Responsable": st.column_config.CheckboxColumn("🍳 Responsable", disabled=True),
                "Payé": st.column_config.CheckboxColumn("💶 Règlement Validé")
            },
            disabled=["N°", "Nom & Prénom"],
            hide_index=True,
            key="editeur_compta_unique",
            use_container_width=True
        )
        
        # Répercussion immédiate des paiements validés
        for _, row in edited_compta.iterrows():
            edited_presents.loc[edited_presents["N°"] == row["N°"], "Payé"] = row["Payé"]


# --- ACTIONS DE SAUVEGARDE ET TÉLÉCHARGEMENT ---
st.write("---")

if st.button(f"💾 ENREGISTRER LE FICHIER : {FICHIER_AGAPE}", type="primary", use_container_width=True):
    edited_presents.to_csv(FICHIER_AGAPE, index=False)
    st.success(f"✅ Fichier '{FICHIER_AGAPE}' enregistré avec succès sur le serveur !")
    st.rerun()

# --- RÉSUMÉ STATISTIQUE ---
st.write("---")
st.subheader("📊 Résumé du repas")
col1, col2, col3 = st.columns(3)
with col1:
    nb_presents = edited_presents[edited_presents["Présent"] == True].shape[0]
    st.metric("Total Présents", nb_presents)
with col2:
    resp = edited_presents[edited_presents["Responsable"] == True]
    st.metric("Responsables", len(resp))
    if not resp.empty:
        st.caption(", ".join(resp["Nom & Prénom"].astype(str)))
with col3:
    nb_paye = edited_presents[(edited_presents["Présent"] == True) & (edited_presents["Payé"] == True)].shape[0]
    st.metric("Règlements perçus", f"{nb_paye} / {nb_presents}")

# --- ZONE DE TÉLÉCHARGEMENT COMPATIBLE IPHONE ---
st.write("---")
st.subheader("📥 Récupérer le fichier de cette soirée")
csv_data = edited_presents.to_csv(index=False).encode('utf-8')
st.download_button(
    label=f"⬇️ Télécharger le fichier {FICHIER_AGAPE}",
    data=csv_data,
    file_name=FICHIER_AGAPE,
    mime="text/csv",
    use_container_width=True
)
