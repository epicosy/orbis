from dataclasses import dataclass
from pydoc import locate
from typing import Any, List, Tuple, Callable

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

#st.markdown("""
#<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
#""", unsafe_allow_html=True)


@dataclass
class InputWidget:
    name: str
    key: str
    type: str


@dataclass
class MultiSelect:
    parameter: str
    options: List[Any]

#class Section:
#    def __init__(self, name: str):
#        self.name = name


if 'endpoints' not in st.session_state:
    r = requests.get(url=f"{base_url}/describe")
    st.session_state.endpoints = r.json()

if 'inputs' not in st.session_state:
    st.session_state.inputs = {}

if 'responses' not in st.session_state:
    st.session_state.responses = {}

    for el in st.session_state.endpoints.keys():
        st.session_state.responses[el] = {}


def list_tests(response: dict):
    _, res = next(iter(response.items()))

    cases = [f"{k}: {v['file']}" for k, v in res['oracle']['cases'].items()]

    return cases


def list_povs(response: list):
    cases = []
    for cmd in response:
        for k, v in cmd['returns'].items():
            cases.append(f"{k}: {v['file']}")

    return cases


def submit_form(endpoint: str, form_name: str, params: List[InputWidget], parse_response: Callable = None):
    json_data = {}

    for p in params:
        if st.session_state[p.key]:
            _type = locate(p.type)
            json_data[p.name] = _type(st.session_state[p.key])
        else:
            json_data[p.name] = None

    url = f"{base_url}/{endpoint}"
    st.info(f"Posting: url:{url} ; data: {json_data}")
    res = requests.post(url=url, json=json_data)

    if res.status_code == 200:
        st.session_state.responses[endpoint]['last'] = res.json()

        if parse_response is not None:
            out = parse_response(res.json())
        else:
            out = res.json()
        if isinstance(out, list):
            for el in out:
                st.success(el)
        else:
            st.success(out)
    else:
        err = f"{res.status_code}"

        try:
            err = res.json()['error']
        except Exception:
            pass

        st.error(err)


def create_form(endpoint: str, oid: str, oid_param: str = None, parse_response: Callable = None,
                multiselect: MultiSelect = None):
    params = []
    form_name = f"{oid}_{endpoint}_form"

    with st.form(form_name):
        for param, (_type, default) in st.session_state.endpoints[endpoint].items():
            key = f"{param}_{oid}"
            params.append(InputWidget(name=param, key=key, type=_type))

            if oid_param and oid_param == param:
                st.session_state[key] = oid
                continue

            t = locate(_type)

            if multiselect and multiselect.parameter == param:
                st.multiselect(label=multiselect.parameter, key=key, options=multiselect.options)
                continue

            if t == str:
                if default is None:
                    st.text_input(param, key=key)
                else:
                    st.text_input(param, default, key=key)

            elif t == int:
                if default is None:
                    st.slider(param, 0, 100, 1, key=key)
                else:
                    st.slider(param, 0, 100, default)
                params.append(InputWidget(name=param, key=key, type=_type))

            elif t == bool:
                if default is None:
                    st.checkbox(param, key=key)
                else:
                    st.checkbox(param, default, key=key)

            elif t == list:
                if default is None:
                    st.text_area(param, [], key=key)
                else:
                    st.text_area(param, default, key=key)

            else:
                if not default:
                    st.text_area(param, key=key)
                else:
                    st.text_area(param, default, key=key)

        submit_btn = st.form_submit_button("Submit", on_click=submit_form,
                                     kwargs={'endpoint': endpoint, 'form_name': form_name, 'params': params,
                                             'parse_response': parse_response})
        if submit_btn:
            st.success(f"'{endpoint}' form for {oid} submitted.")


with st.sidebar:
    selected = option_menu("Orbis", ["Projects", 'Vulnerabilities', 'Instances', 'Configs'],
                           icons=['git', 'bug', 'box-arrow-in-down', 'sliders'], menu_icon="compass", default_index=0)

if selected == "Projects":
    if 'projects' not in st.session_state:
        r = requests.get(url=f"{base_url}/projects")
        st.session_state.projects = r.json()

    cols = st.columns(3)

    for i, (id, p) in enumerate(st.session_state.projects.items()):
        container = cols[i%3].container()
        container.header(id)
        container.subheader(p['name'])

        with container.expander("Generate Tests", expanded=False):
            create_form(endpoint='gen_tests', oid=id, oid_param='pid', parse_response=list_tests)

        with container.expander("Generate POVs", expanded=False):
            create_form(endpoint='gen_povs', oid=id, oid_param='pid', parse_response=list_povs)

        with container.expander("Raw Json", expanded=False):
            st.write(p)


if selected == "Vulnerabilities":
    if 'vulns' not in st.session_state:
        r = requests.get(url=f"{base_url}/vulns")
        st.session_state.vulns = r.json()

    cols = st.columns(3)

    for i, (id, v) in enumerate(st.session_state.vulns.items()):
        container = cols[i%3].container()
        container.header(id)
        container.subheader(v[id]['generic'][0])

        with container.expander("Checkout", expanded=False):
            create_form(endpoint='checkout', oid=id, oid_param='vid')

        with container.expander("Raw Json", expanded=False):
            st.write(v)


if selected == "Instances":
    r = requests.get(url=f"{base_url}/instances")
    instances = r.json()
    cols = st.columns(3)
    last = None

    if 'last' in st.session_state.responses['checkout'] and instances:
        iid = st.session_state.responses['checkout']['last']['iid']
        last = list(instances)[-1]

        st.write(instances[last])
        container = cols[0].container()
        container.header(instances[last]['id'])
        container.subheader(instances[last]['path'])

        with container.expander("Build", expanded=False):
            create_form(endpoint='build', oid=iid, oid_param='iid')

        if instances[last]['pointer'] is not None:
            with container.expander("Test", expanded=False):
                create_form(endpoint='test', oid=iid, oid_param='iid')

        with container.expander("Raw Json", expanded=False):
            st.write(instances[last])

        del instances[last]

    for i, (id, instance) in enumerate(instances.items(), 1 if last else 0):
        container = cols[i % 3].container()
        container.header(id)
        container.subheader(instance['path'])

        with container.expander("Build", expanded=False):
            create_form(endpoint='build', oid=id, oid_param='iid')

        if instance['pointer'] is not None:
            with container.expander("Test", expanded=False):
                tests = list(st.session_state.projects[instance['pid']]['oracle']['cases'].keys())
                create_form(endpoint='test', oid=id, oid_param='iid', multiselect=MultiSelect('tests', tests))

        with container.expander("Raw Json", expanded=False):
            st.write(instance)
