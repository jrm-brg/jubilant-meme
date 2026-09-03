from anvil import *
import anvil.server
from anvil.tables import app_tables

class SaisieAgape(ColumnPanel):
    def __init__(self, **properties):
        self.init_components(**properties)
        
        self.add_component(Label(text="Saisie des Présences à l'Agape", role="headline"))
        
        # Sélection de l'Agape
        agapes = app_tables.agapes.search()
        self.drop_agape = DropDown(
            placeholder="Sélectionner une agape...",
            include_placeholder=True
        )
        self.drop_agape.items = [(f"{a['date']} - {a['description']}", a) for a in agapes]
        self.drop_agape.set_event_handler('change', self.afficher_grille_membres)
        self.add_component(self.drop_agape)
        
        self.panel_membres = ColumnPanel()
        self.add_component(self.panel_membres)

    def afficher_grille_membres(self, **event_args):
        self.panel_membres.clear()
        agape_selectionnee = self.drop_agape.selected_value
        if not agape_selectionnee:
            return

        self.inputs = []
        membres = app_tables.membres.search(tables.order_by("nom"))
        
        for m in membres:
            row_panel = LinearPanel()
            row_panel.add_component(Label(text=f"{m['nom']} {m['prenom']}", width=200))
            
            chk_present = CheckBox(text="Présent")
            chk_paye = CheckBox(text="Payé")
            drop_mode = DropDown(items=["CB", "Chèque", "Espèces", "Virement"])
            
            row_panel.add_component(chk_present)
            row_panel.add_component(chk_paye)
            row_panel.add_component(drop_mode)
            
            self.panel_membres.add_component(row_panel)
            self.inputs.append({
                'membre': m,
                'present_box': chk_present,
                'paye_box': chk_paye,
                'mode_drop': drop_mode
            })
            
        btn_valider = Button(text="Enregistrer la séance", role="primary-color")
        btn_valider.set_event_handler('click', self.valider_seance)
        self.panel_membres.add_component(btn_valider)

    def valider_seance(self, **event_args):
        agape = self.drop_agape.selected_value
        data_to_send = []
        
        for item in self.inputs:
            data_to_send.append({
                'membre': item['membre'],
                'present': item['present_box'].checked,
                'paye': item['paye_box'].checked,
                'mode': item['mode_drop'].selected_value
            })
            
        anvil.server.call('enregistrer_seance', agape, data_to_send)
        Notification("Présences et règlements enregistrés avec succès !").show()
