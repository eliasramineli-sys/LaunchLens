import argparse
import sys
from pathlib import Path
import joblib
import pandas as pd
from .data import generate_data,validate_features
from .modeling import recommend


def main():
    parser=argparse.ArgumentParser(description="LaunchLens | laboratório com dados sintéticos")
    sub=parser.add_subparsers(dest="command",required=True)
    generate=sub.add_parser("generate",help="Regenera somente os CSVs fictícios")
    generate.add_argument("--root",type=Path,default=Path.cwd())
    run=sub.add_parser("run",help="Gera dados, treina, avalia e exporta relatórios")
    run.add_argument("--root",type=Path,default=Path.cwd())
    predict=sub.add_parser("predict",help="Pontua candidatos usando modelo já treinado")
    predict.add_argument("--input",type=Path,required=True)
    predict.add_argument("--output",type=Path,required=True)
    predict.add_argument("--model",type=Path,default=Path("models/launchlens.joblib"))
    args=parser.parse_args()
    try:
        if args.command=="generate":
            h,c=generate_data();base=args.root/"data/raw";base.mkdir(parents=True,exist_ok=True)
            h.to_csv(base/"historico_apps.csv",index=False);c.to_csv(base/"candidatos_apps.csv",index=False)
            print(f"Gerados {len(h)} históricos e {len(c)} candidatos em {base}")
        elif args.command=="run":
            from .experiment import run_experiment
            result=run_experiment(args.root)
            print(f"Modelo: {result['selected_model']} | ROC-AUC teste: {result['test']['roc_auc']:.3f}")
            print("Resultados em reports/ e data/processed/. Somente dados sintéticos.")
        else:
            # Nunca abra joblib recebido de terceiros: pickle pode executar código.
            bundle=joblib.load(args.model)
            df=pd.read_csv(args.input);x=validate_features(df)
            p=bundle["model"].predict_proba(x)[:,1]
            df["prob_sucesso"]=p
            df["recomendacao"]=recommend(p,bundle["threshold"],bundle["band"])
            args.output.parent.mkdir(parents=True,exist_ok=True)
            df.to_csv(args.output,index=False)
            print(f"Pontuados {len(df)} candidatos: {args.output}")
    except (ValueError,FileNotFoundError) as exc:
        print(f"Erro: {exc}",file=sys.stderr)
        raise SystemExit(2) from exc


if __name__=="__main__":
    main()
