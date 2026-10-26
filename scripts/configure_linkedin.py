"""Execute localmente. Recebe token via prompt oculto e salva em GitHub Secrets."""
import getpass
import json
import re
import subprocess
import urllib.request
import urllib.error

REPO = "eliasramineli-sys/LaunchLens"


def cli(*args, value=None):
    p = subprocess.run(["gh", *args], input=value, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError("GitHub CLI falhou. Execute gh auth login e confira acesso ao LaunchLens.")


def main():
    cli("auth", "status")
    print("Gere um token no portal oficial do LinkedIn com openid, profile e w_member_social.")
    token = getpass.getpass("Cole o access token (não será exibido): ").strip()
    if not token:
        raise ValueError("Token vazio.")
    req = urllib.request.Request("https://api.linkedin.com/v2/userinfo",
                                  headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            profile = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError):
        raise RuntimeError("Não foi possível consultar o perfil. Confira token e escopos openid/profile.") from None
    sub = profile.get("sub", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", sub):
        raise ValueError("Identificador de perfil inválido.")
    print("Conta autorizada:", profile.get("name", "Nome não informado"))
    if input("Salvar essa autorização no LaunchLens? Digite SIM: ").strip() != "SIM":
        print("Configuração cancelada.");return
    cli("secret", "set", "LINKEDIN_ACCESS_TOKEN", "--repo", REPO, value=token)
    cli("variable", "set", "LINKEDIN_AUTHOR_URN", "--repo", REPO, "--body", "urn:li:person:" + sub)
    cli("variable", "set", "LINKEDIN_API_VERSION", "--repo", REPO, "--body", "202610")
    print("Credenciais configuradas. Não foi publicado nenhum post.")
    print("Revise a prévia e depois defina LINKEDIN_ENABLED=true nas Variables do GitHub.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        raise SystemExit(str(exc))
