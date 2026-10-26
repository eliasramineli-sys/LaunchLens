"""Publicação por Release; biblioteca padrão + GitHub CLI. Sem retentativa de POST."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE_NAME = "linkedin-publication.json"


def gh(*args, binary=False):
    p = subprocess.run(["gh", *args], capture_output=True)
    if p.returncode:
        # Não ecoar stderr do CLI: evite divulgação acidental de dados de autenticação.
        raise RuntimeError("Falha no GitHub CLI. Confira autenticação e permissão contents:write.")
    return p.stdout if binary else p.stdout.decode("utf-8")


def release_metadata(repo, tag):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Repositório inválido.")
    # Query por tag é codificada para não alterar o endpoint.
    from urllib.parse import quote
    release = json.loads(gh("api", f"repos/{repo}/releases/tags/{quote(tag, safe='')}"))
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Somente Releases estáveis já publicadas são aceitas.")
    expected = f"https://github.com/{repo}/releases/tag/"
    if not release["html_url"].startswith(expected):
        raise ValueError("URL da Release não corresponde ao repositório.")
    return release


def render_post(release, repo, template):
    tag = release["tag_name"]
    if any(ord(c) < 32 for c in tag) or len(tag) > 150:
        raise ValueError("Tag inválida para divulgação.")
    text = template.format(release_tag=tag, release_url=release["html_url"],
                           repository_url=f"https://github.com/{repo}").strip()
    if not text or len(text) > 2800:
        raise ValueError("Texto vazio ou maior que 2.800 caracteres; revise social/linkedin_post.txt.")
    return text


def payload_for(author, text):
    if not re.fullmatch(r"urn:li:person:[A-Za-z0-9_-]+", author):
        raise ValueError("LINKEDIN_AUTHOR_URN deve identificar uma pessoa autorizada.")
    return {"author": author, "commentary": text, "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                             "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}


def send_post(token, author, text, version):
    if not token:
        raise ValueError("Secret LINKEDIN_ACCESS_TOKEN ausente.")
    if not re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", version):
        raise ValueError("LINKEDIN_API_VERSION deve usar YYYYMM.")
    req = urllib.request.Request("https://api.linkedin.com/rest/posts",
        data=json.dumps(payload_for(author, text)).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "Linkedin-Version": version, "X-Restli-Protocol-Version": "2.0.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            if response.status != 201:
                raise RuntimeError("Resposta inesperada; confira o LinkedIn antes de repetir.")
            urn = response.headers.get("x-restli-id", "")
            if not re.fullmatch(r"urn:li:(share|ugcPost):\d+", urn):
                raise RuntimeError("Resposta sem identificador; confira o LinkedIn antes de repetir.")
            return urn
    except urllib.error.HTTPError as exc:
        messages = {401: "Token expirado ou inválido; autorize novamente.",
                    403: "Acesso recusado; confira produto e permissão w_member_social.",
                    429: "Limite de chamadas atingido."}
        raise RuntimeError(f"LinkedIn HTTP {exc.code}. " + messages.get(exc.code,
            "Confira versão da API, permissões e publicação no LinkedIn.")) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Falha de conexão; a publicação pode ter sido recebida. Confira antes de repetir.") from None


def publish_release(repo, release, text, sender=send_post, github=gh):
    # O registro pending é gravado ANTES do POST; falhas ambíguas não geram repetição automática.
    if any(a["name"] == STATE_NAME for a in release.get("assets", [])):
        return "blocked_existing_record"
    author = os.environ.get("LINKEDIN_AUTHOR_URN", "")
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    version = os.environ.get("LINKEDIN_API_VERSION", "202610")
    payload_for(author, text)
    if not token:
        raise ValueError("Configure LINKEDIN_ACCESS_TOKEN antes de ativar a publicação.")
    state = {"status": "pending", "release_id": release["id"], "tag": release["tag_name"],
             "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
             "run_id": os.environ.get("GITHUB_RUN_ID", "local")}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / STATE_NAME
        def record(overwrite=False):
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            args = ["release", "upload", release["tag_name"], str(path), "--repo", repo]
            if overwrite: args.append("--clobber")
            github(*args)
        record()
        urn = sender(token, author, text, version)
        state.update(status="published", post_urn=urn,
                     post_url=f"https://www.linkedin.com/feed/update/{urn}/")
        record(overwrite=True)
    return state["post_url"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "eliasramineli-sys/LaunchLens"))
    p.add_argument("--tag", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    try:
        release = release_metadata(args.repo, args.tag)
        text = render_post(release, args.repo, (ROOT / "social/linkedin_post.txt").read_text(encoding="utf-8"))
        if args.dry_run:
            print("PRÉVIA — nenhuma publicação enviada:\n\n" + text)
            summary = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary, "a", encoding="utf-8") as f:
                    f.write("## Prévia LinkedIn (sem envio)\n\n" + text + "\n")
            return
        if os.environ.get("LINKEDIN_ENABLED") != "true":
            raise ValueError("Defina a variável LINKEDIN_ENABLED=true após revisar a prévia.")
        result = publish_release(args.repo, release, text)
        if result == "blocked_existing_record":
            print("Envio bloqueado: esta Release já tem registro. Consulte o asset linkedin-publication.json.")
        else:
            print("Publicado: " + result)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print("Erro: " + str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
