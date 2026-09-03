import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime, date

@anvil.server.callable
def get_dashboard_metrics():
    """Calcule le total des impayés et le nombre de membres."""
    total_impayes = 0.0
    all_presences = app_tables.presences.search()
    
    for p in all_presences:
        du = p['montant_du'] or 0.0
        paye = p['montant_paye'] or 0.0
        if du > paye:
            total_impayes += (du - paye)
            
    nb_membres = len(app_tables.membres.search())
    return {
        'total_impayes': total_impayes,
        'nb_membres': nb_membres
    }

@anvil.server.callable
def get_liste_impayes():
    """Retourne la liste détaillée de tous les impayés."""
    impayes = []
    all_presences = app_tables.presences.search()
    
    for p in all_presences:
        du = p['montant_du'] or 0.0
        paye = p['montant_paye'] or 0.0
        if du > paye:
            membre = p['membre']
            agape = p['agape']
            impayes.append({
                'presence_row': p,
                'nom': membre['nom'] if membre else '',
                'prenom': membre['prenom'] if membre else '',
                'date_agape': agape['date'] if agape else None,
                'reste_du': du - paye
            })
    return impayes

@anvil.server.callable
def regulariser_impaye(presence_row, montant_regle, mode_paiement):
    """Met à jour un paiement partiel ou total."""
    du = presence_row['montant_du'] or 0.0
    ancien_paye = presence_row['montant_paye'] or 0.0
    nouveau_paye = ancien_paye + montant_regle
    
    presence_row.update(
        montant_paye=nouveau_paye,
        mode_paiement=mode_paiement,
        date_paiement=date.today()
    )

@anvil.server.callable
def enregistrer_seance(agape_row, enregistrements):
    """
    Enregistre les présences et paiements d'une séance.
    `enregistrements` est une liste de dicts : 
    [{'membre': row, 'present': bool, 'paye': bool, 'mode': str}]
    """
    tarif = agape_row['tarif'] or 0.0
    
    for item in enregistrements:
        m = item['membre']
        present = item['present']
        est_paye = item['paye']
        mode = item['mode']
        
        montant_du = tarif if present else 0.0
        montant_paye = tarif if (present and est_paye) else 0.0
        
        # Vérifie si la ligne existe déjà
        existante = app_tables.presences.get(agape=agape_row, membre=m)
        if existante:
            existante.update(
                present=present,
                montant_du=montant_du,
                montant_paye=montant_paye,
                mode_paiement=mode if est_paye else None
            )
        else:
            app_tables.presences.add_row(
                agape=agape_row,
                membre=m,
                present=present,
                montant_du=montant_du,
                montant_paye=montant_paye,
                mode_paiement=mode if est_paye else None,
                date_paiement=date.today() if est_paye else None
            )
