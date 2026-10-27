# PoC para os stakeholders

Como colocar o SIGI no ar para os stakeholders verem e testarem o fluxo de
ATA → insumos → NE, com dados fictícios. **Não é produção**: o seed é de
desenvolvimento (`APP_ENV=development`) e as senhas são conhecidas.

## 1. Subir o sistema

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.cli seed-dev-admin
docker compose exec backend python -m app.cli seed-demo
```

O `seed-demo` carrega ATAs, insumos e quatro NEs, uma em cada ponto do fluxo:
Demanda, Validação de saldo, Pré-empenho (o saldo aparece como `700 (300)`) e
NE emitida. Logins: `admin@sc.gov.br` / `admin` (gestor),
`servidor@sc.gov.br` / `servidor` e `auditor@sc.gov.br` / `auditor`.

Depois de atualizar o código: `docker compose up --build -d` e
`alembic upgrade head` de novo. O container não roda migrações sozinho.

## 2. Mostrar para eles

**Opção A — hoje, sem custo, a partir do seu computador.** Um túnel publica a
porta 3000 num endereço HTTPS temporário:

```bash
cloudflared tunnel --url http://localhost:3000
```

Ele imprime um endereço `https://….trycloudflare.com`; mande esse link. Fica no
ar enquanto o computador e o comando estiverem rodando. Só o frontend precisa
sair: ele fala com a API por dentro, no mesmo endereço.

**Opção B — sempre no ar: uma VM pequena.** Uma e2-small no GCP, ou qualquer
VPS com Docker. Clone o repositório, rode o passo 1 e coloque o Caddy na
frente para ter HTTPS com um domínio:

```
sigi-poc.exemplo.gov.br {
  reverse_proxy localhost:3000
}
```

Feche no firewall as portas 5432 e 8000; só a 443 precisa estar aberta.

## 3. Roteiro sugerido

1. Entrar como gestor e abrir **ATAs** → `DEMO-001/2026`: o bloco **Saldo**
   mostra o disponível com o reservado entre parênteses.
2. **Notas de empenho** → abrir a NE em Pré-empenho e avançar até NE emitida,
   digitando o número: o saldo do item passa de `700 (300)` para `700`.
3. **Abrir NE** numa ATA com pouco saldo e tentar o pré-empenho: o bloqueio
   mostra o disponível e o necessário.
4. Entrar como servidor: ele avança etapas, mas não reverte nem cancela.
