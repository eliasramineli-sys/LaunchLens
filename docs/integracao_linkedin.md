# GitHub → LinkedIn: ativação do LaunchLens

## O que já está implementado

Uma Release estável publicada no GitHub aciona `.github/workflows/linkedin-release.yml`.
Enquanto `LINKEDIN_ENABLED` não for `true`, o fluxo gera apenas uma prévia do texto.
Depois de autorizar sua conta e ativar a variável, novas Releases geram um post público com
texto e links. Não há upload de imagem nesta versão. O projeto e o Power BI continuam no GitHub.
O texto completo está em [`social/linkedin_post.txt`](../social/linkedin_post.txt).
Não existe geração de texto por API de IA, servidor contratado nem serviço externo de agendamento.

## 1. Criar e autorizar o aplicativo no LinkedIn

1. Abra https://www.linkedin.com/developers/apps e escolha **Create app**.
2. Use um nome como **LaunchLens Publisher** e complete os campos exigidos pelo portal.
   A criação pode exigir uma **LinkedIn Page** associada e verificação por um administrador.
   Seu perfil pessoal não substitui essa Page; use uma Page que você administra.
3. Na aba **Products**, solicite/habilite **Share on LinkedIn** e
   **Sign In with LinkedIn using OpenID Connect**. Aguarde a disponibilização dos produtos.
4. No [gerador oficial de tokens](https://www.linkedin.com/developers/tools/oauth/token-generator),
   selecione seu aplicativo e as permissões **openid**, **profile** e **w_member_social**.
5. Autorize com a conta de Elias e gere um **access token**. Ele será usado somente na sua máquina
   para configurar o GitHub. Não envie o token, Client Secret ou código de autorização pelo chat,
   não cole em arquivos do repositório e não tire capturas com esses valores.

Se o gerador não permitir os escopos, os produtos ainda não estão liberados para seu app.
Não troque por cookies de sessão ou automação de senha: conclua a habilitação oficial.
O assistente consulta `/v2/userinfo`, usa o identificador retornado pelo app e mostra o nome
para você confirmar a conta; a URL pública do perfil não é uma credencial.

## 2. Configurar o GitHub no Windows

Instale Python 3.12, Git e o [GitHub CLI](https://cli.github.com/).
Se já tem uma cópia local do repositório, use `git pull`; caso contrário:

```powershell
git clone https://github.com/eliasramineli-sys/LaunchLens.git
cd LaunchLens
```

Entre no GitHub CLI com sua conta e execute o assistente:

```powershell
gh auth login
py -3.12 scripts/configure_linkedin.py
```

O assistente pede o token em um prompt oculto, consulta a conta no LinkedIn, mostra o nome e
solicita `SIM` para salvar a configuração. Usa a conexão local do GitHub CLI para configurar:

| Local no GitHub | Nome | Valor |
| --- | --- | --- |
| Actions Secret | LINKEDIN_ACCESS_TOKEN | Token OAuth autorizado |
| Actions Variable | LINKEDIN_AUTHOR_URN | Identificador da pessoa retornado pela API |
| Actions Variable | LINKEDIN_API_VERSION | 202610 |

O token é passado ao CLI pela entrada padrão, não por argumento de processo. Não fica salvo em
arquivo pelo assistente. A configuração pode ser parcial se o GitHub recusar uma gravação;
corrija o acesso e execute novamente. Não é pedido Client Secret.

Alternativa: crie o Secret e as Variables manualmente em **Settings → Secrets and variables → Actions**.
Para o autor, use `urn:li:person:ID`, com o ID obtido pela API para o mesmo app/token; não use `eliasramineli`.

## 3. Revisar e testar a prévia

1. Revise `social/linkedin_post.txt` no GitHub e ajuste a apresentação se desejar.
   Somente `{release_tag}`, `{repository_url}` e `{release_url}` são substituídos.
2. Crie uma Release estável em **Releases → Draft a new release**. Para a primeira divulgação,
   uma opção é tag `v1.0.0`, branch `main`, título `LaunchLens 1.0.0`.
3. Ao publicar essa Release, o workflow executa em prévia, porque a ativação está ausente.
4. Abra **Actions → Divulgar Release no LinkedIn**, selecione a execução e leia o resumo/saída.
   A prévia não chama a API de publicação e não exige token do LinkedIn.

Releases já existentes não são divulgadas retroativamente. A execução manual exige uma Release
estável já publicada; não basta existir uma tag. Drafts e prereleases são rejeitados.

## 4. Ativar e divulgar a primeira versão

Após conferir conta, texto e prévia:

1. Em **Settings → Secrets and variables → Actions → Variables**, crie
   **LINKEDIN_ENABLED** com o valor exato **true**.
2. Em **Actions → Divulgar Release no LinkedIn → Run workflow**, use a branch **main**,
   informe a tag da Release e marque **Enviar ao LinkedIn**.
3. Execute. O link do post aparece na saída após sucesso.
4. A partir daí, novas Releases estáveis publicadas disparam o envio automaticamente.

Para testar localmente uma Release existente, sem publicar:

```powershell
py -3.12 scripts/publish_linkedin.py --tag v1.0.0 --dry-run
```

Para pausar, altere `LINKEDIN_ENABLED` para **false** ou desabilite o workflow. Não precisa apagar o projeto.

## Duplicidade e falhas

Antes do POST, a automação grava um asset `linkedin-publication.json` na Release com `status=pending`.
Após sucesso, substitui o registro por `status=published` e salva o identificador/link do post.
O registro não contém token. Reexecuções encontram esse asset e bloqueiam o novo envio.
O workflow serializa execuções da mesma Release com `concurrency` e nunca cancela uma execução que está publicando.

Se o envio falhar, o registro pending permanece: não há retentativa automática, pois um timeout pode
ocorrer depois de o LinkedIn já ter publicado. Verifique o perfil primeiro. Se o post existe, mantenha
o registro. **Somente se confirmar que não houve publicação**, exclua o asset na Release e execute
manualmente outra vez. Isso é proteção operacional, não uma garantia distribuída de exactly-once.
Não apague/recrie Releases para tentar repetir; isso remove o histórico de deduplicação.

- **401**: token inválido/expirado; autorize novamente e execute o assistente para atualizar o Secret.
- **403**: produto, escopo ou autorização insuficiente; confira `w_member_social` e o autor.
- **400/426**: revise o texto e a versão suportada da API; atualize `LINKEDIN_API_VERSION` se necessário.
- **429**: limite de chamadas; confira se houve publicação antes de tentar novamente.
- Falha ao criar asset: confira permissão **contents:write** e políticas de Actions. O POST não é enviado
  se a reserva não puder ser registrada.

Tokens possuem validade: use o prazo mostrado pelo gerador e renove antes de expirar.
Não foi implementada renovação automática; refresh tokens dependem do acesso concedido pelo LinkedIn.
As versões da API também têm ciclo de suporte e precisam de manutenção.

## Verificação e limites

Os testes locais simulam criação de registro, chamada de publicação, duplicidade, timeout, token ausente,
prévia e erros de autenticação. Nenhum token real é usado nos testes.
Não foi realizado teste ponta a ponta autenticado: o usuário precisa habilitar seu app e autorizar a conta.
A publicação é texto com links; o LinkedIn pode não gerar uma prévia visual automaticamente pela API.
Não modifica a seção Destaques, não compra anúncios e não adiciona métricas fictícias ao post.

O Actions usa `ubuntu-latest` padrão. Em repositórios públicos, esses runners são gratuitos conforme
as regras do GitHub. Não exige assinatura de serviço de automação ou API de IA.

## Referências oficiais

- https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
- https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2
- https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs
