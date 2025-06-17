import os
import streamlit.components.v1 as components

parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "frontend/build")
_component_func = components.declare_component("easy_mde", path=build_dir)


def easy_mde(key=None, value="", height=300):
    component_value = _component_func(
        key=key, value=value, height=height, default=value)
    return component_value
