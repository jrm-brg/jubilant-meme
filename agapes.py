import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Gestion des Agapes", layout="wide")
st.title("🍽️ Gestionnaire Évolué des Agapes")

LOCAL_CSV = "Tableau de Loge - Contacts.csv"
HISTORIQUE_CSV = "historique_agapes.csv"
GOOGLE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFcguChCFkKz3hLvlSmMdDgVR8WEf3XUI1DWmNGMNXL3N_qN3ErV0X3BEVpZ9xYuMPdYJn-7SBcP94/pub?gid=355758587&single=true&output=csv"

# 1. Chargement du fichier local ou distant
if os.path.exists(LOCAL_CSV):
    df_contacts = pd.read_csv(LOCAL_CSV)
else:
    try:
        df_contacts = pd.read_csv(GOOGLE_CSV_URL)
        df_contacts.to_csv(LOCAL_CSV, index=False)
    except Exception as e:
        st.error(f"Erreur de chargement initial : {e}")
        st.stop()

# --- 🛠️ NETTOYAGE ET HARMONISATION DES COLONNES ---
df_contacts.columns = df_contacts.columns.str.strip()

rename_dict = {}
for col in df_contacts.columns:
    col_clean = col.lower().replace("é", "e").replace("û", "u").replace("°", "").replace(" ", "")
    if col_clean in ["n", "no", "id", "num", "numero"]:
        rename_dict[col] = "N°"
    elif col_clean in ["nom&prenom", "nomprenom", "identite", "membres"]:
        rename_dict[col] = "Nom & Prénom"
    elif col_clean in ["portable", "tel", "telephone", "mobile"]:
        rename_dict[col] = "Portable"
    elif col_clean in ["email", "mail"]:
        rename_dict[col] = "Email"

df_contacts = df_contacts.rename(columns=rename_dict)

if "N°" not in df_contacts.columns:
    df_contacts.insert(0, "N°", range(1, len(df_contacts) + 1))

if "Nom & Prénom" not in df_contacts.columns:
    st.error("🚨 La colonne 'Nom & Prénom' est introuvable. Vérifiez votre fichier CSV.")
    st.stop()

for col in ["Présent", "Règlement Validé", "Responsable Agapes"]:
    if col in df_contacts.columns:
        df_contacts = df_contacts.drop(columns=[col])

# 2. Chargement de l'historique
if os.path.exists(HISTORIQUE_CSV):
    df_hist = pd.read_csv(HISTORIQUE_CSV)
else:
    df_hist = pd.DataFrame(columns=["Date", "N°", "Présent", "Responsable", "Payé"])

df_contacts["N°"] = df_contacts["N°"].astype(int)
if not df_hist.empty:
    df_hist["N°"] = df_hist["N°"].astype(int)


# --- MENU LATÉRAL ---
st.sidebar.header("👤 1 - Ajouter un contact")
with st.sidebar.form(key="add_form", clear_on_submit=True):
    new_nom = st.text_input("Nom")
    new_prenom = st.text_input("Prénom")
    
    # Case à cocher pour basculer l'affichage du formulaire
    est_visiteur = st.checkbox("👤 Cette personne est un Visiteur")
    
    # 🌟 MODIFICATION DYNAMIQUE : Champs conditionnels selon le type de personne
    if est_visiteur:
        new_association = st.text_input("Nom de son association / loge")
        new_ville = ""
        new_tel = ""
        new_email = ""
    else:
        new_association = ""
        new_ville = st.text_input("Ville (optionnel)")
        new_tel = st.text_input("Portable")
        new_email = st.text_input("Email")
        
    submit_button = st.form_submit_button(label="Ajouter à la base")

    if submit_button:
        if new_nom and new_prenom:
            if est_visiteur and not new_association:
                st.sidebar.error("Le nom de l'association est obligatoire pour un visiteur.")
            else:
                new_no = int(df_contacts["N°"].max() + 1) if not df_contacts.empty else 1
                
                # Formatage personnalisé pour le visiteur
                if est_visiteur:
                    nom_complet = f"{new_nom.upper()} {new_prenom} ({new_association})"
                else:
                    nom_complet = f"{new_nom.upper()} {new_prenom}"
                
                new_row = {
                    "N°": new_no, "Nom & Prénom": nom_complet, 
                    "Portable": new_tel, "Email": new_email
                }
                if "Ville" in df_contacts.columns:
                    new_row["Ville"] = new_ville.upper() if new_ville else "—"

                df_contacts = pd.concat([df_contacts, pd.DataFrame([new_row])], ignore_index=True)
                df_contacts.to_csv(LOCAL_CSV, index=False)
                st.sidebar.success(f"✅ {nom_complet} ajouté !")
                st.rerun()
        else:
            st.sidebar.error("Le Nom et le Prénom sont obligatoires.")

st.sidebar.write("---")

st.sidebar.header("📅 2 - Sélection de la Date")
nouvelle_date = st.sidebar.date_input("Créer une nouvelle date :", datetime.now())
date_str = nouvelle_date.strftime("%d/%m/%Y")

dates_existantes = df_hist["Date"].unique().tolist() if not df_hist.empty else []
if date_str not in dates_existantes:
    dates_existantes.insert(0, date_str)

date_selectionnee = st.sidebar.selectbox("Date de l'Agape à gérer :", dates_existantes)


# --- PRÉPARATION DU TABLEAU DU JOUR ---
df_date_reunion = df_hist[df_hist["Date"] == date_selectionnee]

if df_date_reunion.empty:
    initial_rows = []
    for _, row in df_contacts.iterrows():
        initial_rows.append({"Date": date_selectionnee, "N°": int(row["N°"]), "Présent": False, "Responsable": False, "Payé": False})
    df_date_reunion = pd.DataFrame(initial_rows)

df_mapping = pd.merge(df_contacts[["N°", "Nom & Prénom"]], df_date_reunion, on="N°", how="left")
df_mapping["Présent"] = df_mapping["Présent"].fillna(False).astype(bool)
df_mapping["Responsable"] = df_mapping["Responsable"].fillna(False).astype(bool)
df_mapping["Payé"] = df_mapping["Payé"].fillna(False).astype(bool)


# --- ONGLETS INTERFACES ---
onglet1, onglet2 = st.tabs(["👥 1. Présences & Responsables", "💶 2. Règlements (Filtré)"])

with onglet1:
    st.header(f"Pointage du {date_selectionnee}")
    st.write("Cochez les membres présents et les responsables.")
    
    edited_presents = st.data_editor(
        df_mapping,
        column_config={
            "N°": st.column_config.NumberColumn(disabled=True),
            "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
            "Présent": st.column_config.CheckboxColumn("👍 Présent"),
            "Responsable": st.column_config.CheckboxColumn("🍳 Responsable"),
            "Payé": st.column_config.CheckboxColumn("💶 Payé", disabled=True),
            "Date": None
        },
        disabled=["N°", "Nom & Prénom"],
        hide_index=True,
        key="editeur_presents",
        use_container_width=True
    )

with onglet2:
    st.header(f"Encaisser les règlements du {date_selectionnee}")
    df_presents_uniquement = edited_presents[edited_presents["Présent"] == True]
    
    if df_presents_uniquement.empty:
        st.warning("⚠️ Aucun membre n'est coché 'Présent' pour le moment dans le premier onglet.")
    else:
        st.write(f"Voici la liste des **{len(df_presents_uniquement)} présents**. Cochez les paiements :")
        
        edited_compta = st.data_editor(
            df_presents_uniquement,
            column_config={
                "N°": st.column_config.NumberColumn(disabled=True),
                "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                "Présent": None, 
                "Responsable": st.column_config.CheckboxColumn("🍳 Responsable", disabled=True),
                "Payé": st.column_config.CheckboxColumn("💶 Règlement Validé"),
                "Date": None
            },
            disabled=["N°", "Nom & Prénom"],
            hide_index=True,
            key="editeur_compta",
            use_container_width=True
        )
        
        for _, row in edited_compta.iterrows():
            edited_presents.loc[edited_presents["N°"] == row["N°"], "Payé"] = row["Payé"]

# --- ENREGISTREMENT ---
st.write("---")
if st.button("💾 ENREGISTRER TOUT POUR CETTE DATE", type="primary", use_container_width=True):
    df_to_save = edited_presents[["Date", "N°", "Présent", "Responsable", "Payé"]]
    if not df_hist.empty:
        df_hist = df_hist[df_hist["Date"] != date_selectionnee]
    df_hist = pd.concat([df_hist, df_to_save], ignore_index=True)
    df_hist.to_csv(HISTORIQUE_CSV, index=False)
    st.success(f"✅ Données du {date_selectionnee} sauvegardées avec succès !")
    st.rerun()

# --- STATISTIQUES ---
st.write("---")
st.subheader("📊 Résumé de cette session")
col1, col2, col3 = st.columns(3)
with col1:
    nb_presents = edited_presents[edited_presents["Présent"] == True].shape[0]
    st.metric("Total Présents", nb_presents)
with col2:
    resp = edited_presents[edited_presents["Responsable"] == True]
    st.metric("Nombre de Responsables", len(resp))
    if not resp.empty:
        st.caption(", ".join(resp["Nom & Prénom"].astype(str)))
with col3:
    nb_paye = edited_presents[(edited_presents["Présent"] == True) & (edited_presents["Payé"] == True)].shape[0]
    st.metric("Règlements Reçus", f"{nb_paye} / {nb_presents}")


# --- SAUVEGARDE ET TÉLÉCHARGEMENT ---
st.write("---")
st.subheader("💾 Sauvegarde & Sécurité des données")
col_down1, col_down2 = st.columns(2)

with col_down1:
    csv_historique = df_hist.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger l'Historique des Agapes (.csv)",
        data=csv_historique,
        file_name=f"historique_agapes_maj_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_down2:
    csv_contacts = df_contacts.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger le Fichier Contacts à jour (.csv)",
        data=csv_contacts,
        file_name="Tableau de Loge - Contacts.csv",
        mime="text/csv",
        use_container_width=True
    )
