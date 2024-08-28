import streamlit as st
import json
from pydantic import BaseModel, Field, create_model
from typing import Any, Dict, List

def save_to_indexeddb(data):
    js_code = f"""
    var data = {json.dumps(data)};
    var request = indexedDB.open("MyDatabase", 1);
    request.onupgradeneeded = function(event) {{
        var db = event.target.result;
        var objectStore = db.createObjectStore("MyObjectStore", {{ keyPath: "id" }});
    }};
    request.onsuccess = function(event) {{
        var db = event.target.result;
        var transaction = db.transaction(["MyObjectStore"], "readwrite");
        var objectStore = transaction.objectStore("MyObjectStore");
        data.forEach(function(item) {{
            item.id = crypto.randomUUID();
            objectStore.add(item);
        }});
    }};
    """
    st.components.v1.html(f"<script>{js_code}</script>", height=0)

def load_from_indexeddb():
    js_code = """
    <script>
    function loadData() {
        var request = indexedDB.open("MyDatabase", 1);
        request.onsuccess = function(event) {
            var db = event.target.result;
            var transaction = db.transaction(["MyObjectStore"], "readonly");
            var objectStore = transaction.objectStore("MyObjectStore");
            var request = objectStore.getAll();
            request.onsuccess = function(event) {
                var data = event.target.result;
                if (data.length > 0) {
                    window.parent.postMessage({type: "FROM_JAVASCRIPT", data: data}, "*");
                }
            };
        };
    }
    loadData();
    </script>
    """
    st.components.v1.html(js_code, height=0)

def infer_type(value: Any) -> Any:
    if isinstance(value, bool):
        return bool
    elif isinstance(value, int):
        return int
    elif isinstance(value, float):
        return float
    elif isinstance(value, list):
        return List[infer_type(value[0]) if value else Any]
    elif isinstance(value, dict):
        return Dict[str, Any]
    else:
        return str

def create_pydantic_model(json_data: Dict[str, Any]):
    fields = {}
    for key, value in json_data.items():
        fields[key] = (infer_type(value), Field(...))
    
    DynamicModel = create_model("DynamicModel", **fields)
    st.session_state.model = DynamicModel