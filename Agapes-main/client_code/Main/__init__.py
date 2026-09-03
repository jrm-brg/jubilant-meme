from ._anvil_designer import MainTemplate
from anvil import *
import anvil.server
from ..Dashboard import Dashboard
from ..SaisieAgape import SaisieAgape
from ..Annuaire import Annuaire

class Main(MainTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.nav_dashboard_click()

    def nav_dashboard_click(self, **event_args):
        self.content_panel.clear()
        self.content_panel.add_component(Dashboard())

    def nav_saisie_click(self, **event_args):
        self.content_panel.clear()
        self.content_panel.add_component(SaisieAgape())

    def nav_annuaire_click(self, **event_args):
        self.content_panel.clear()
        self.content_panel.add_component(Annuaire())
