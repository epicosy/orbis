import streamlit as st
import requests
import json
from streamlit_option_menu import option_menu
#import streamlit.components.v1 as stc

base_url = "http://172.17.0.2:8080"

st.set_page_config(
     page_title="Orbis UI",
     layout="wide",
     initial_sidebar_state="expanded",
 )

st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
""", unsafe_allow_html=True)

def get_card(id: str, name: str, buttons: list = [], text: str = ""):
    btns = [f'<button class="btn btn-outline-dark"> {b} </button>' for b in buttons]
    btns_str = '\n'.join(btns)
    return f"""
    <div class="card text-dark bg-light mb-3">
        <div class="card-header">{id}</div>
        <div class="card-body">
            <h5 class="card-title text-dark">{name}</h5>
            <p class="card-text">{text}</p>
            {btns_str if btns else "<i></i>"}
        </div>
    </div>
    """

def set_selection(object, id, type):
    st.session_state['id'] = id
    st.session_state['object'] = object
    st.session_state['type'] = type

def checkout(id: str):
    r = requests.post(url=f"{base_url}/checkout", json={'vid': id, 'root_dir': "/nexus"})

    if r.status_code == 200:
        st.info(r.json())
    else:
        st.error(r.status_code)

with st.sidebar:
    selected = option_menu("Orbis", ["Projects", 'Vulnerabilities', 'Instances', 'Post'],
                           icons=['list', 'bug'], menu_icon="compass", default_index=0)

if selected == "Projects":
    r = requests.get(url=f"{base_url}/projects")
    projects = r.json()
    cols = st.columns(3)

    for i, (id, p) in enumerate(projects.items()):
#        card = get_card(id, p['name'], buttons = ['Checkout', 'Compile', 'Test', 'Generate'])
#        cols[i%3].markdown(card, unsafe_allow_html=True)
        container = cols[i%3].container()
        container.header(id)
        container.subheader(p['name'])
        with container.expander("Raw Json", expanded=False):
            st.write(p)
        container.button(id, on_click=set_selection,  kwargs={'id': id, 'object': p, 'type': 'proj'})


if selected == "Vulnerabilities":
    if 'vulns' not in st.session_state:
        r = requests.get(url=f"{base_url}/vulns")
        st.session_state.vulns = r.json()

    cols = st.columns(3)

    for i, (id, v) in enumerate(st.session_state.vulns.items()):
#        card = get_card(id, v[id]['generic'][0])
#        cols[i%3].markdown(card, unsafe_allow_html=True)
        container = cols[i%3].container()
        container.header(id)
        container.subheader(v[id]['generic'][0])
        with container.expander("Raw Json", expanded=False):
            st.write(v)
        container.button(id, on_click=set_selection, kwargs={'id': id, 'object': v, 'type': 'vuln'})
        container.button("Checkout", on_click=checkout, key=f'checkout_{id}', kwargs={'id': id})


if selected == "Instances":
    r = requests.get(url=f"{base_url}/instances")
    instances = r.json()
    cols = st.columns(3)

    for i, (id, v) in enumerate(instances.items()):
        card = get_card(id, v['path'], ['Delete', 'Refresh', 'Expand'])
        cols[i%3].markdown(card, unsafe_allow_html=True)

if selected == "Post":
    if 'object' in st.session_state:
        st.write(st.session_state['object'])
    if 'id' in st.session_state:
        st.write(st.session_state['id'])
    if 'type' in st.session_state:
        st.write(st.session_state['type'])
