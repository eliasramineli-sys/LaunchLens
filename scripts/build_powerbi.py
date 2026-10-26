"""Gera PBIP/PBIR e TMSL com snapshot embutido; não exige caminhos de outra máquina."""
import argparse
import base64
import json
from pathlib import Path
import pandas as pd

BASE="https://developer.microsoft.com/json-schemas/fabric/"
SCHEMAS={"pbip":"pbip/pbipProperties/1.0.0", "pbir":"item/report/definitionProperties/2.0.0",
         "pbism":"item/semanticModel/definitionProperties/1.0.0"}

def schema(name):
    return BASE+SCHEMAS.get(name,"item/report/definition/"+name)+"/schema.json"


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")


def literal(value):
    if isinstance(value,bool):value="true" if value else "false"
    elif isinstance(value,(int,float)):value=str(value)
    else:value="'"+str(value).replace("'","''")+"'"
    return {"expr":{"Literal":{"Value":value}}}


def measure(table,name):
    return {"Measure":{"Expression":{"SourceRef":{"Entity":table}},"Property":name}}


def column(table,name):
    return {"Column":{"Expression":{"SourceRef":{"Entity":table}},"Property":name}}


def projection(table,name,is_measure=False):
    return {"field":measure(table,name) if is_measure else column(table,name),"queryRef":table+"."+name}


def measures():
    return {
      "Candidatos":[
        ("Total candidatos","COUNTROWS(Candidatos)","0"),
        ("Probabilidade media","AVERAGE(Candidatos[prob_sucesso])","0.0%"),
        ("Lancar","CALCULATE(COUNTROWS(Candidatos), Candidatos[recomendacao] = \"Lancar\")","0"),
        ("Validar mais","CALCULATE(COUNTROWS(Candidatos), Candidatos[recomendacao] = \"Validar mais\")","0"),
        ("Adiar","CALCULATE(COUNTROWS(Candidatos), Candidatos[recomendacao] = \"Adiar\")","0"),
        ("Capital desenvolvimento","SUM(Candidatos[custo_desenvolvimento])",'"R$ "#,##0'),
      ],
      "Avaliacao":[
        ("Total teste","COUNTROWS(Avaliacao)","0"),
        ("Falsos positivos","SUM(Avaliacao[fp])","0"),
        ("Falsos negativos","SUM(Avaliacao[fn])","0"),
        ("Precisao","DIVIDE(SUM(Avaliacao[tp]), SUM(Avaliacao[tp]) + SUM(Avaliacao[fp]))","0.0%"),
        ("Recall","DIVIDE(SUM(Avaliacao[tp]), SUM(Avaliacao[tp]) + SUM(Avaliacao[fn]))","0.0%"),
        ("Brier filtrado","AVERAGE(Avaliacao[erro_brier])","0.000"),
        ("Taxa sucesso real","AVERAGE(Avaliacao[sucesso_12m])","0.0%"),
      ],
      "Metricas":[
        ("ROC AUC teste",'CALCULATE(MAX(Metricas[roc_auc]), Metricas[conjunto] = "teste")',"0.000"),
        ("Brier comparacao","MIN(Metricas[brier])","0.000"),
      ],
      "Importancia":[("Queda AUC","SUM(Importancia[importancia_auc])","0.000")],
      "Limiar":[("Custo relativo","MIN(Limiar[custo_relativo])","0.000")],
    }


def build_semantic(root):
    specs={"Candidatos":"candidatos_pontuados", "Avaliacao":"avaliacao_teste",
           "Metricas":"metricas_modelos", "Importancia":"importancia_variaveis", "Limiar":"sensibilidade_limiar"}
    tables=[];dax=[]
    for table,file in specs.items():
        path=root/f"data/processed/{file}.csv";df=pd.read_csv(path)
        cols=[];types=[]
        for c in df:
            if c.startswith("data_"):dt="dateTime";mt="type date";fmt="dd/MM/yyyy"
            elif pd.api.types.is_integer_dtype(df[c]):dt="int64";mt="Int64.Type";fmt="0"
            elif pd.api.types.is_numeric_dtype(df[c]):
                dt="double";mt="type number"
                fmt="0.0%" if any(p in c for p in ["prob_","retencao","ativacao","intencao","roi_","crescimento"]) else "0.00"
            else:dt="string";mt="type text";fmt=None
            col={"name":c,"dataType":dt,"sourceColumn":c,"summarizeBy":"none"}
            if fmt:col["formatString"]=fmt
            cols.append(col);types.append('{"'+c+'", '+mt+'}')
        embedded=base64.b64encode(path.read_bytes()).decode()
        expr=["let",f'    Fonte = if PastaDados = "" then Binary.FromText("{embedded}", BinaryEncoding.Base64)',
              f'        else File.Contents(PastaDados & "/{file}.csv"),',
              f'    CSV = Csv.Document(Fonte, [Delimiter=",", Columns={len(cols)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
              '    Cabecalhos = Table.PromoteHeaders(CSV, [PromoteAllScalars=true]),',
              '    Tipos = Table.TransformColumnTypes(Cabecalhos, {'+', '.join(types)+'}, "en-US")',
              'in','    Tipos']
        ms=[]
        for name,expression,fmt in measures().get(table,[]):
            ms.append({"name":name,"expression":expression,"formatString":fmt,"displayFolder":"Indicadores LaunchLens"})
            dax.append(f"-- Tabela: {table}\n[{name}] = {expression}\n")
        tables.append({"name":table,"columns":cols,"measures":ms,
            "partitions":[{"name":table,"mode":"import","source":{"type":"m","expression":expr}}]})
    model={"name":"LaunchLens","compatibilityLevel":1567,"model":{
        "culture":"pt-BR","defaultPowerBIDataSourceVersion":"powerBI_V3","sourceQueryCulture":"en-US",
        "expressions":[{"name":"PastaDados","kind":"m","expression":'"" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=false]'}],
        "tables":tables,"annotations":[{"name":"PBI_QueryOrder","value":json.dumps(["PastaDados"]+list(specs))}]}}
    save(root/"powerbi/LaunchLens.SemanticModel/model.bim",model)
    save(root/"powerbi/LaunchLens.SemanticModel/definition.pbism",{"$schema":schema("pbism"),"version":"1.0","settings":{"qnaEnabled":False}})
    (root/"powerbi/medidas.dax").write_text("\n".join(dax),encoding="utf-8")


def build_report(root):
    report=root/"powerbi/LaunchLens.Report"
    save(root/"powerbi/LaunchLens.pbip",{"$schema":schema("pbip"),"version":"1.0","artifacts":[{"report":{"path":"LaunchLens.Report"}}],"settings":{"enableAutoRecovery":True}})
    save(report/"definition.pbir",{"$schema":schema("pbir"),"version":"4.0","datasetReference":{"byPath":{"path":"../LaunchLens.SemanticModel"}}})
    theme={"name":"LaunchLens","dataColors":["#2563EB","#0D9488","#E9A23B","#D65A6F","#8B5CF6"],
           "background":"#F4F7FB","foreground":"#102039","tableAccent":"#2563EB"}
    save(report/"StaticResources/RegisteredResources/LaunchLens.json",theme)
    save(report/"definition/report.json",{"$schema":schema("report/2.0.0"),
        "themeCollection":{"customTheme":{"name":"LaunchLens","reportVersionAtImport":"5.59","type":"RegisteredResources"}},
        "resourcePackages":[{"name":"RegisteredResources","type":"RegisteredResources","items":[{"name":"LaunchLens","path":"LaunchLens.json","type":"CustomTheme"}]}]})
    save(report/"definition/version.json",{"$schema":schema("versionMetadata/1.0.0"),"version":"4.0.0"})
    pages=[("portfolio","01 | Decisao de lancamento"),("qualidade","02 | Qualidade e risco"),("fatores","03 | Fatores e politica")]
    save(report/"definition/pages/pages.json",{"$schema":schema("pagesMetadata/1.0.0"),"pageOrder":[p[0] for p in pages],"activePageName":"portfolio"})
    for name,label in pages:
        save(report/f"definition/pages/{name}/page.json",{"$schema":schema("page/1.0.0"),"name":name,"displayName":label,"displayOption":"FitToPage","height":900,"width":1440,
            "objects":{"background":[{"properties":{"color":{"solid":{"color":literal("#F4F7FB")}},"transparency":literal(0)}}]}})
    serial=0
    def visual(page,kind,title,x,y,w,h,roles=None,text=None,sort=None,dark=False):
        nonlocal serial
        serial+=1;name=f"v{serial:04d}"
        cfg={"visualType":kind,"visualContainerObjects":{
            "title":[{"properties":{"show":literal(bool(title)),"text":literal(title),"fontSize":literal(13),"fontColor":{"solid":{"color":literal("#102039")}}}}],
            "background":[{"properties":{"show":literal(True),"color":{"solid":{"color":literal("#102039" if dark else "#FFFFFF")}},"transparency":literal(0)}}],
            "border":[{"properties":{"show":literal(False)}}],
            "visualHeader":[{"properties":{"show":literal(False)}}],
        }}
        if roles:
            cfg["query"]={"queryState":{k:{"projections":v} for k,v in roles.items()}}
            if sort:cfg["query"]["sortDefinition"]={"sort":[{"field":sort[0],"direction":sort[1]}]}
        if text:
            cfg["objects"]={"general":[{"properties":{"paragraphs":[{"textRuns":[{"value":text,"textStyle":{"fontFamily":"Segoe UI","fontSize":"17pt" if dark else "11pt","color":"#FFFFFF" if dark else "#52627A"}}]}]}}]}
        save(report/f"definition/pages/{page}/visuals/{name}/visual.json",{"$schema":schema("visualContainer/2.1.0"),"name":name,
             "position":{"x":x,"y":y,"width":w,"height":h,"z":serial,"tabOrder":serial},"visual":cfg})
    for p,title in pages:
        visual(p,"textbox","",24,18,1392,68,text="LaunchLens  /  "+title[5:]+"  •  DADOS SINTÉTICOS",dark=True)
    visual("portfolio","textbox","",24,95,1392,44,text="Qual aplicativo merece avançar? Selecione categoria e recomendação; revise evidências antes de aprovar.")
    for i,(measure_name,title) in enumerate([("Total candidatos","Candidatos avaliados"),("Lancar","Lançar"),("Validar mais","Validar mais"),("Adiar","Adiar")]):
        visual("portfolio","card",title,24+i*352,150,336,104,{"Values":[projection("Candidatos",measure_name,True)]})
    visual("portfolio","slicer","Categoria",24,270,260,140,{"Values":[projection("Candidatos","categoria")]})
    visual("portfolio","slicer","Recomendação",24,426,260,140,{"Values":[projection("Candidatos","recomendacao")]})
    visual("portfolio","clusteredBarChart","Probabilidade média por categoria",300,270,548,296,
           {"Category":[projection("Candidatos","categoria")],"Y":[projection("Candidatos","Probabilidade media",True)]},sort=(measure("Candidatos","Probabilidade media"),"Descending"))
    visual("portfolio","clusteredColumnChart","Capital de desenvolvimento por decisão (R$)",864,270,552,296,
           {"Category":[projection("Candidatos","recomendacao")],"Y":[projection("Candidatos","Capital desenvolvimento",True)]})
    visual("portfolio","tableEx","Ranking dos candidatos | probabilidade, custo e decisão",24,582,1392,258,
           {"Values":[projection("Candidatos",c) for c in ["ranking","app_id","categoria","plataforma","prob_sucesso","recomendacao","custo_desenvolvimento","limiar_adiar","limiar_lancar"]]},sort=(column("Candidatos","ranking"),"Ascending"))
    visual("portfolio","textbox","",24,848,1392,40,text="A decisão usa cortes definidos na validação. Probabilidade de sucesso ≠ lucro previsto. Nenhum candidato tem desfecho observado.")
    for i,(t,m,title) in enumerate([("Metricas","ROC AUC teste","ROC-AUC | teste inteiro"),("Avaliacao","Precisao","Precisão | corte binário"),("Avaliacao","Recall","Recall | corte binário"),("Avaliacao","Brier filtrado","Brier | menor é melhor")]):
        visual("qualidade","card",title,24+i*352,108,336,110,{"Values":[projection(t,m,True)]})
    visual("qualidade","tableEx","Comparação de modelos | validação + teste apenas do vencedor",24,238,860,266,
           {"Values":[projection("Metricas",c) for c in ["modelo","conjunto","roc_auc","brier","precisao","recall","limiar"]]})
    visual("qualidade","clusteredColumnChart","Erros de classificação no teste",900,238,516,266,
           {"Y":[projection("Avaliacao","Falsos positivos",True),projection("Avaliacao","Falsos negativos",True)]})
    visual("qualidade","clusteredColumnChart","Casos por classe real e prevista",24,524,860,274,
           {"Category":[projection("Avaliacao","classe_real")],"Series":[projection("Avaliacao","classe_modelo")],"Y":[projection("Avaliacao","Total teste",True)]})
    visual("qualidade","card","Aplicativos no teste",900,524,516,122,{"Values":[projection("Avaliacao","Total teste",True)]})
    visual("qualidade","card","Taxa de sucesso observada",900,666,516,132,{"Values":[projection("Avaliacao","Taxa sucesso real",True)]})
    visual("qualidade","textbox","",24,816,1392,64,text="Teste temporal com desfechos maduros e embargos de 12 meses. Classificação binária e política com revisão humana são avaliações diferentes. As tabelas de métricas e avaliação não se filtram entre si.")
    visual("fatores","clusteredBarChart","Quais sinais o modelo mais utiliza? | permutação na validação",24,108,850,526,
           {"Category":[projection("Importancia","variavel")],"Y":[projection("Importancia","Queda AUC",True)]},sort=(measure("Importancia","Queda AUC"),"Descending"))
    visual("fatores","lineChart","Sensibilidade ao corte | custo 2×FP + FN por app",894,108,522,332,
           {"Category":[projection("Limiar","limiar")],"Y":[projection("Limiar","Custo relativo",True)]},sort=(column("Limiar","limiar"),"Ascending"))
    s=json.loads((root/"reports/resumo_resultados.json").read_text())
    visual("fatores","textbox","",894,458,522,176,text=f"POLÍTICA ILUSTRATIVA\nLançar: p ≥ {s['limiar_lancar']:.2f}\nValidar: {s['limiar_adiar']:.2f} ≤ p < {s['limiar_lancar']:.2f}\nAdiar: p < {s['limiar_adiar']:.2f}\nPesos de erro sem unidade monetária.")
    visual("fatores","textbox","",24,654,1392,210,text="COMO INTERPRETAR\nA importância mede a queda de ROC-AUC ao embaralhar uma variável. Não demonstra causalidade. Variáveis correlacionadas podem dividir importância.\nA faixa de revisão é uma regra de governança; não é um intervalo de confiança. O custo do gráfico é relativo, sem valor em reais.\nPara aplicar ao mercado: substituir os dados fictícios por histórico com desfechos maduros, verificar viés de seleção e validar novamente.")
    return serial


def build(root):
    build_semantic(root);count=build_report(root)
    print(f"Power BI gerado: 3 páginas, {count} visuais, 5 tabelas. Validação Desktop pendente.")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    build(p.parse_args().root)
