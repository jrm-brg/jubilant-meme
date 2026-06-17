import streamlit as st
import pandas as pd
import os
import requests
import base64
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Gestion des Agapes", layout="wide")
st.title("🍽️ Gestionnaire d'Agapes (Sauvegarde GitHub)")

LOCAL_CSV = "Tableau de Loge - Contacts.csv"
# Lecture directe de votre fichier de contact mis à jour sur GitHub
URL_RAW_GITHUB = "https://raw.githubusercontent.com/jrm-brg/Agapes/main/Tableau%20de%20Loge%20-%20Contacts.csv"

# Configuration pour l'API GitHub (Récupération des Secrets)
REPO_OWNER = "jrm-brg"
REPO_NAME = "Agapes"
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    GITHUB_TOKEN = None
    st.warning("⚠️ Le Secret 'GITHUB_TOKEN' n'est pas configuré sur Streamlit Cloud. La sauvegarde automatique sur GitHub sera désactivée.")

# 1. Chargement des contacts
try:
    df_contacts = pd.read_csv(URL_RAW_GITHUB)
except Exception as e:
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
df_membres_base = df_contacts[["N°", "Nom & Prénom"]].copy()


# --- FONCTION DE SAUVEGARDE DIRECTE SUR GITHUB ---
def sauvegarder_sur_github(nom_fichier, dataframe):
    if not GITHUB_TOKEN:
        st.error("Impossible de sauvegarder : Clé GitHub manquante dans les Secrets.")
        return False
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{nom_fichier}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    content_csv = dataframe.to_csv(index=False)
    content_bytes = content_csv.encode("utf-8")
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    
    # Étape A : Vérifier si le fichier existe déjà pour obtenir son identifiant unique (SHA)
    sha = None
    reponse_get = requests.get(url, headers=headers)
    if reponse_get.status_code == 200:
        sha = reponse_get.json().get("sha")
        
    # Étape B : Envoyer ou mettre à jour le fichier
    data = {
        "message": f"Mise à jour automatique : {nom_fichier} via l'application iPhone",
        "content": content_b64
    }
    if sha:
        data["sha"] = sha
        
    reponse_put = requests.put(url, headers=headers, json=data)
    if reponse_put.status_code in [200, 201]:
        return True
    else:
        st.error(f"Erreur GitHub API : {reponse_put.json().get('message')}")
        return False


# --- MENU LATÉRAL : DATE & VISITEURS ---
st.sidebar.header("📅 1 - Choisir la Date")
nouvelle_date = st.sidebar.date_input("Sélectionner une date :", datetime.now())
date_str = nouvelle_date.strftime("%d_%m_%Y")
date_affichage = nouvelle_date.strftime("%d/%m/%Y")

FICHIER_AGAPE = f"Agape_{date_str}.csv"

# Tentative de récupération du fichier de la soirée (depuis GitHub en priorité si existant)
if f"df_cache_{date_str}" not in st.session_state:
    url_fichier_soir = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FICHIER_AGAPE}"
    try:
        res = requests.get(url_fichier_soir)
        if res.status_code == 200:
            st.session_state[f"df_cache_{date_str}"] = pd.read_csv(url_fichier_soir)
        else:
            initial_rows = [{"N°": int(row["N°"]), "Nom & Prénom": row["Nom & Prénom"], "Présent": False, "Responsable": False, "Payé": False} for _, row in df_membres_base.iterrows()]
            st.session_state[f"df_cache_{date_str}"] = pd.DataFrame(initial_rows)
    except Exception:
        initial_rows = [{"N°": int(row["N°"]), "Nom & Prénom": row["Nom & Prénom"], "Présent": False, "Responsable": False, "Payé": False} for _, row in df_membres_base.iterrows()]
        st.session_state[f"df_cache_{date_str}"] = pd.DataFrame(initial_rows)

df_session = st.session_state[f"df_cache_{date_str}"]
df_session["N°"] = df_session["N°"].astype(int)

st.sidebar.write("---")
st.sidebar.header("👤 2 - Ajouter un Visiteur")
with st.sidebar.form(key="visiteur_form", clear_on_submit=True):
    v_nom = st.text_input("Nom")
    v_prenom = st.text_input("Prénom")
    v_loge = st.text_input("Loge / Association")
    v_ville = st.text_input("Ville")
    submit_v = st.form_submit_button("Ajouter le visiteur ce soir")

    if submit_v:
        if v_nom and v_prenom and v_loge:
            next_id = int(df_session["N°"].max() + 1) if not df_session.empty else 9000
            identite_visiteur = f"{v_nom.upper()} {v_prenom} ({v_loge} - {v_ville if v_ville else '—'})"
            new_v_row = {"N°": next_id, "Nom & Prénom": identite_visiteur, "Présent": True, "Responsable": False, "Payé": False}
            df_session = pd.concat([df_session, pd.DataFrame([new_v_row])], ignore_index=True)
            st.session_state[f"df_cache_{date_str}"] = df_session
            st.sidebar.success("✅ Visiteur ajouté (Pensez à enregistrer en bas) !")
            st.rerun()

# --- INTERFACE PRINCIPALE ---
st.header(f"🍽️ Gestion du repas du {date_affichage}")
onglet1, onglet2 = st.tabs(["👥 1. Présences & Responsables", "💶 2. Règlements (Filtré)"])

with onglet1:
    edited_presents = st.data_editor(
        df_session,
        column_config={
            "N°": st.column_config.NumberColumn(disabled=True),
            "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
            "Présent": st.column_config.CheckboxColumn("👍 Présent(e)"),
            "Responsable": st.column_config.CheckboxColumn("🍳 Responsable Agape"),
            "Payé": st.column_config.CheckboxColumn("💶 Payé", disabled=True)
        },
        disabled=["N°", "Nom & Prénom"], hide_index=True, key=f"editor_p_{date_str}", use_container_width=True
    )

with onglet2:
    df_presents_uniquement = edited_presents[edited_presents["Présent"] == True]
    if df_presents_uniquement.empty:
        st.warning("⚠️ Cochez d'abord des personnes présentes dans le premier onglet.")
    else:
        edited_compta = st.data_editor(
            df_presents_uniquement,
            column_config={
                "N°": st.column_config.NumberColumn(disabled=True),
                "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                "Présent": None, "Responsable": st.column_config.CheckboxColumn("🍳 Responsable", disabled=True),
                "Payé": st.column_config.CheckboxColumn("💶 Règlement Validé")
            },
            disabled=["N°", "Nom & Prénom"], hide_index=True, key=f"editor_c_{date_str}", use_container_width=True
        )
        for _, row in edited_compta.iterrows():
            edited_presents.loc[edited_presents["N°"] == row["N°"], "Payé"] = row["Payé"]

st.session_state[f"df_cache_{date_str}"] = edited_presents

# --- 🚀 BOUTON ENREGISTRER DIRECTEMENT SUR GITHUB 🚀 ---
st.write("---")
if st.button(f"🚀 ENREGISTRER ET ENVOYER DIRECTEMENT SUR GITHUB", type="primary", use_container_width=True):
    with st.spinner("Envoi du fichier vers GitHub en cours..."):
        succes = sauvegarder_sur_github(FICHIER_AGAPE, edited_presents)
        if succes:
            st.success(f"🎉 Le fichier '{FICHIER_AGAPE}' a été enregistré et poussé avec succès sur GitHub !")
            st.ballons()

# --- STATISTIQUES ---
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
