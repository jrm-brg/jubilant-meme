from anvil import *
import anvil.server

class Dashboard(ColumnPanel):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.charger_donnees()

    def charger_donnees(self):
        self.clear()
        metrics = anvil.server.call('get_dashboard_metrics')
        
        # En-tête
        self.add_component(Label(text="Tableau de Bord & Impayés", role="headline"))
        
        # Métriques
        self.add_component(Label(text=f"Total Membres : {metrics['nb_membres']}"))
        self.add_component(Label(text=f"Reste à recouvrer : {metrics['total_impayes']:.2f} €", role="title"))
        
        # Tableau des impayés
        impayes = anvil.server.call('get_liste_impayes')
        if impayes:
            grid = DataGrid()
            grid.columns = [
                {"id": "nom", "title": "Nom", "data_key": "nom"},
                {"id": "prenom", "title": "Prénom", "data_key": "prenom"},
                {"id": "date", "title": "Agape du", "data_key": "date_agape"},
                {"id": "reste", "title": "Reste Dû (€)", "data_key": "reste_du"}
            ]
            
            panel = RepeatingPanel()
            panel.items = impayes
            grid.add_component(panel)
            self.add_component(grid)
        else:
            self.add_component(Label(text="Aucun impayé en cours. Tout est à jour !"))
