import json

tpl_meta_json = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/knowledge_jsons/TPL_meta_0.91_20250709.json"

with open(tpl_meta_json, 'r') as json_data:
    tpl_meta = json.load(json_data)

libraries = tpl_meta.get("libraries", [])
tpl_names = [lib["name"] for lib in libraries
             if "name" in lib
             and len(lib["name"]) > 3
             and lib['name'] not in ['file', 'make','tree','server','date','system','linux', 'absent', 'check', 'context', 'sender', 'opener', 'leaf', 'safe', 'bind', 'attr']]

print(len(tpl_names))
print(tpl_names)