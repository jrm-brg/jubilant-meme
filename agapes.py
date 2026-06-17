import streamlit as st
import pandas as pd
import os
import requests
import base64
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Gestion des Agapes", layout="wide")
st.title("🍽️ Gestionnaire d'Agapes Évolué")

LOCAL_CSV = "Tableau de Loge - Contacts.csv"
URL_RAW_GITHUB = "https://raw.githubusercontent.com/jrm-brg/Agapes/main/Tableau%20de%20Loge%20-%20Contacts.csv"

REPO_OWNER = "jrm-brg"
REPO_NAME = "Agapes"
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    GITHUB_TOKEN = None
    st.warning("⚠️ Le Secret 'GITHUB_TOKEN' n'est pas configuré sur Streamlit Cloud.")

# 1. Chargement des contacts de base
@st.cache_data(ttl=60)
def charger_contacts():
    try:
        df = pd.read_csv(URL_RAW_GITHUB)
    except Exception:
        if os.path.exists(LOCAL_CSV):
            df = pd.read_csv(LOCAL_CSV)
        else:
            return pd.DataFrame(columns=["N°", "Nom & Prénom"])
    
    df.columns = df.columns.str.strip()
    rename_dict = {}
    for col in df.columns:
        col_clean = col.lower().replace("é", "e").replace("û", "u").replace("°", "").replace(" ", "")
        if col_clean in ["n", "no", "id", "num", "numero"]:
            rename_dict[col] = "N°"
        elif col_clean in ["nom&prenom", "nomprenom", "identite", "membres"]:
            rename_dict[col] = "Nom & Prénom"
    df = df.rename(columns=rename_dict)
    if "N°" not in df.columns:
        df.insert(0, "N°", range(1, len(df) + 1))
    df["N°"] = df["N°"].astype(int)
    return df[["N°", "Nom & Prénom"]].copy()

df_membres_base = charger_contacts()

# --- FONCTIONS GITHUB API ---
def sauvegarder_sur_github(nom_fichier, dataframe):
    if not GITHUB_TOKEN:
        st.error("Jeton GitHub manquant dans les Secrets.")
        return False
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{nom_fichier}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content_b64 = base64.b64encode(dataframe.to_csv(index=False).encode("utf-8")).decode("utf-8")
    sha = None
    res_get = requests.get(url, headers=headers)
    if res_get.status_code == 200:
        sha = res_get.json().get("sha")
    data = {"message": f"Mise à jour : {nom_fichier}", "content": content_b64}
    if sha: data["sha"] = sha
    res_put = requests.put(url, headers=headers, json=data)
    return res_put.status_code in [200, 201]

def lister_fichiers_agapes_github():
    if not GITHUB_TOKEN: return []
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            fichiers = [f["name"] for f in res.json() if f["name"].startswith("Agape_") and f["name"].endswith(".csv")]
            return fichiers
    except Exception:
        pass
    return []

# --- MENU LATÉRAL ---
st.sidebar.header("📅 1 - Choisir la Date")
nouvelle_date = st.sidebar.date_input("Sélectionner une date :", datetime.now())
date_str = nouvelle_date.strftime("%d/%m/%Y")
file_date_str = nouvelle_date.strftime("%d_%m_%Y")
FICHIER_AGAPE = f"Agape_{file_date_str}.csv"

# Chargement des données de la session en cours
if f"df_{file_date_str}" not in st.session_state:
    url_file = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FICHIER_AGAPE}"
    try:
        res = requests.get(url_file)
        if res.status_code == 200:
            st.session_state[f"df_{file_date_str}"] = pd.read_csv(url_file)
        else:
            rows = [{"N°": int(r["N°"]), "Nom & Prénom": r["Nom & Prénom"], "Présent": False, "Payé": False} for _, r in df_membres_base.iterrows()]
            st.session_state[f"df_{file_date_str}"] = pd.DataFrame(rows)
    except Exception:
        rows = [{"N°": int(r["N°"]), "Nom & Prénom": r["Nom & Prénom"], "Présent": False, "Payé": False} for _, r in df_membres_base.iterrows()]
        st.session_state[f"df_{file_date_str}"] = pd.DataFrame(rows)

df_session = st.session_state[f"df_{file_date_str}"]
df_session["N°"] = df_session["N°"].astype(int)

st.sidebar.write("---")
st.sidebar.header("👤 2 - Ajouter un Visiteur")
with st.sidebar.form(key="v_form", clear_on_submit=True):
    v_nom = st.text_input("Nom")
    v_prenom = st.text_input("Prénom")
    v_loge = st.text_input("Loge / Association")
    v_ville = st.text_input("Ville")
    if st.form_submit_button("Ajouter le visiteur ce soir"):
        if v_nom and v_prenom and v_loge:
            next_id = int(df_session["N°"].max() + 1) if not df_session.empty else 9000
            identite = f"{v_nom.upper()} {v_prenom} ({v_loge} - {v_ville if v_ville else '—'})"
            new_v = {"N°": next_id, "Nom & Prénom": identite, "Présent": True, "Payé": False}
            df_session = pd.concat([df_session, pd.DataFrame([new_v])], ignore_index=True)
            st.session_state[f"df_{file_date_str}"] = df_session
            st.sidebar.success("✅ Visiteur ajouté (Enregistrez en bas) !")
            st.rerun()

# --- INTERFACE PRINCIPALE ---
onglet1, onglet2, onglet3 = st.tabs(["👥 1. Pointage Inscriptions", "💶 2. Règlements", "📊 3. Historique Général"])

# --- ONGLET 1 : POINTAGE (FILTRÉ : Uniquement les non-cochés) ---
with onglet1:
    st.header(f"Pointage des présents pour le {date_str}")
    
    # Section d'annulation d'erreur d'inscription
    df_presents_courants = df_session[df_session["Présent"] == True]
    if not df_presents_courants.empty:
        with st.expander("⚠️ Besoin d'annuler une inscription / corriger une erreur ?"):
            p_a_annuler = st.selectbox(
                "Sélectionnez la personne à retirer des présents :", 
                df_presents_courants["Nom & Prénom"].tolist(),
                key="select_annulation"
            )
            if st.button("❌ Retirer cette personne de la liste des présents", type="secondary"):
                row_cible = df_session[df_session["Nom & Prénom"] == p_a_annuler].iloc[0]
                
                # Si c'est un visiteur (ID >= 9000), on le supprime complètement
                if int(row_cible["N°"]) >= 9000:
                    df_session = df_session[df_session["Nom & Prénom"] != p_a_annuler]
                else:
                    # Si c'est un membre de base, on le remet à zéro (Absent, non payé)
                    df_session.loc[df_session["Nom & Prénom"] == p_a_annuler, ["Présent", "Payé"]] = False
                
                st.session_state[f"df_{file_date_str}"] = df_session
                st.toast(f"🔄 Inscription annulée pour {p_a_annuler}")
                st.rerun()

    st.write("---")
    df_non_pointes = df_session[df_session["Présent"] == False]
    
    if df_non_pointes.empty:
        st.success("🎉 Tout le monde a été pointé présent ou absent pour cette date !")
    else:
        st.caption(f"Il reste {len(df_non_pointes)} personnes à pointer.")
        edited_p = st.data_editor(
            df_non_pointes,
            column_config={
                "N°": st.column_config.NumberColumn(disabled=True),
                "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                "Présent": st.column_config.CheckboxColumn("👍 Présent(e)"),
                "Payé": None
            },
            disabled=["N°", "Nom & Prénom"], hide_index=True, key=f"ed_p_{file_date_str}", use_container_width=True
        )
        
        # Répercuter les changements immédiats
        for _, row in edited_p.iterrows():
            if row["Présent"]:
                df_session.loc[df_session["N°"] == row["N°"], "Présent"] = row["Présent"]
                st.session_state[f"df_{file_date_str}"] = df_session
                st.rerun()

# --- ONGLET 2 : RÈGLEMENTS (FILTRÉ : Uniquement les présents) ---
with onglet2:
    st.header(f"Règlements du {date_str}")
    df_presents = df_session[df_session["Présent"] == True]
    
    if df_presents.empty:
        st.info("⚠️ En attente de pointage dans le premier onglet pour voir apparaître les personnes ici.")
    else:
        nb_non_payes = df_presents[df_presents["Payé"] == False].shape[0]
        if nb_non_payes == 0:
            st.success("✅ Tous les présents de ce soir ont payé !")
        else:
            st.warning(f"💶 {nb_non_payes} règlements restants à percevoir.")

        edited_c = st.data_editor(
            df_presents,
            column_config={
                "N°": st.column_config.NumberColumn(disabled=True),
                "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                "Présent": None,
                "Payé": st.column_config.CheckboxColumn("💶 Règlement Validé")
            },
            disabled=["N°", "Nom & Prénom"], hide_index=True, key=f"ed_c_{file_date_str}", use_container_width=True
        )
        
        for _, row in edited_c.iterrows():
            df_session.loc[df_session["N°"] == row["N°"], "Payé"] = row["Payé"]
        st.session_state[f"df_{file_date_str}"] = df_session

# --- 🚀 BOUTON ENREGISTRER DIRECTEMENT SUR GITHUB 🚀 ---
st.write("---")
try:
    if st.button(f"🚀 ENREGISTRER LA SOIRÉE DU {date_str} SUR GITHUB", type="primary", use_container_width=True):
        with st.spinner("Envoi du fichier vers GitHub..."):
            succes = sauvegarder_sur_github(FICHIER_AGAPE, df_session)
            if succes:
                st.success(f"🎉 Enregistré avec succès sur GitHub !")
                st.balloons()
            else:
                st.error("❌ GitHub a refusé l'enregistrement. Vérifiez votre GITHUB_TOKEN dans les Secrets.")
except Exception as erreur_cachee:
    st.error(f"💥 L'application a planté lors de l'envoi : {erreur_cachee}")

# --- ONGLET 3 : HISTORIQUE ET SUIVI DES IMPAYÉS ---
with onglet3:
    st.header("📊 Contrôle de tous les historiques d'Agapes")
    
    if st.button("🔄 Actualiser et Scanner tous les fichiers GitHub"):
        st.cache_data.clear()
        st.rerun()
        
    liste_fichiers = lister_fichiers_agapes_github()
    
    if not liste_fichiers:
        st.info("Aucun fichier d'Agape enregistré trouvé sur GitHub pour le moment.")
    else:
        st.write(f"🔎 Analyse de **{len(liste_fichiers)} repas** enregistrés...")
