"""Valida PBIP/PBIR contra cópias dos esquemas oficiais Microsoft, offline."""
import base64
import io
import json
from pathlib import Path
import pandas as pd
from jsonschema import Draft7Validator
from referencing import Registry,Resource


def validate(root):
    root=Path(root)
    cache=json.loads((root/"powerbi/schema_cache.json").read_text())
    registry=Registry().with_resources((u,Resource.from_contents(s)) for u,s in cache.items())
    n=0
    for f in (root/"powerbi").rglob("*"):
        if not f.is_file() or f.suffix not in [".json",".pbip",".pbir",".pbism"] or f.name=="schema_cache.json":continue
        obj=json.loads(f.read_text())
        if "$schema" in obj:
            u=obj["$schema"];validator=Draft7Validator(cache[u],registry=registry)
            errors=list(validator.iter_errors(obj))
            if errors:
                raise ValueError(f"{f.relative_to(root)}: {errors[0].message}")
            n+=1
    model=json.loads((root/"powerbi/LaunchLens.SemanticModel/model.bim").read_text())
    tables={t["name"]:t for t in model["model"]["tables"]}
    refs=0
    # Verifica todos os campos/medidas usados em visuais.
    def walk(obj):
        nonlocal refs
        if isinstance(obj,dict):
            for typ in ["Column","Measure"]:
                if typ in obj:
                    expr=obj[typ];source=expr.get("Expression",{}).get("SourceRef",{})
                    if "Entity" in source:
                        table=tables[source["Entity"]];key="columns" if typ=="Column" else "measures"
                        assert expr["Property"] in {x["name"] for x in table.get(key,[])},expr
                        refs+=1
            for v in obj.values():walk(v)
        elif isinstance(obj,list):
            for v in obj:walk(v)
    for f in (root/"powerbi/LaunchLens.Report").rglob("visual.json"):walk(json.loads(f.read_text()))
    specs={"Candidatos":"candidatos_pontuados","Avaliacao":"avaliacao_teste","Metricas":"metricas_modelos","Importancia":"importancia_variaveis","Limiar":"sensibilidade_limiar"}
    for table in tables.values():
        line=table["partitions"][0]["source"]["expression"][1]
        payload=line.split('Binary.FromText("',1)[1].split('"',1)[0]
        snapshot=base64.b64decode(payload)
        assert snapshot==(root/f"data/processed/{specs[table['name']]}.csv").read_bytes(),"Snapshot desatualizado"
        frame=pd.read_csv(io.BytesIO(snapshot))
        assert list(frame.columns)==[c["name"] for c in table["columns"]]
    print(f"OK: {n} documentos PBIP/PBIR; {refs} referências; 5 snapshots conferidos.")
    print("Esquemas JSON não validam execução de M/DAX nem renderização no Power BI Desktop.")
    return n


if __name__=="__main__":validate(Path(__file__).resolve().parents[1])
