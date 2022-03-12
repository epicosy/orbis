import streamlit as st
import requests
import json
from streamlit_option_menu import option_menu


with st.sidebar:
    selected = option_menu("Orbis", ["Projects", 'Vulnerabilities'],
                           icons=['list', 'bug'], menu_icon="compass", default_index=1)
    print(selected)

if selected == "Projects":
    r = requests.get("http://10.227.157.101:8080/projects")
    print(r.status_code)
    print(json.dumps(r.json()))
