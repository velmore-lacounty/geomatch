from shiny import App
from ui import app_ui
from server import server

# Create the app using the UI and server components
app = App(app_ui, server)

# To deploy app to Posit Connect: 
# rsconnect deploy shiny . --server http://pdlpositcontgis.hosted.lac.com --api-key DQhA57GoaJvSeAGGMPMn9Qy9KoIOKFoc --title "GeoMatch"
