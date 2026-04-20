from shiny import App
from ui import app_ui
from server import server

# Create the app using the UI and server components
app = App(app_ui, server)
