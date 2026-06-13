# SIGI — Sistema Integrado de Gestão de Insumos

Plataforma web para rastreamento do ciclo completo de insumos em entidades governamentais estaduais — da ATA à conclusão do fornecimento.

![Status](https://img.shields.io/badge/status-em%20progresso-yellow)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js-informational)

---

## Sobre o Projeto

O SIGI centraliza e digitaliza o ciclo de rastreamento de insumos, substituindo planilhas e e-mails dispersos por uma plataforma web auditável e em tempo real.

O sistema acompanha cada insumo do início ao fim: da abertura de uma ATA de Registro de Preços, passando pelo fluxo de Notas de Empenho, até o registro das Notas Fiscais e o encerramento do fornecimento. Todo o histórico é imutável e exportável para prestação de contas.

**Stack:** Python · FastAPI (backend) — Next.js (frontend) — PostgreSQL

---

## Instalação e Execução

### Pré-requisitos

- [Docker](https://docs.docker.com) e Docker Compose
- [Node.js](https://nodejs.org) 20+
- [Python](https://python.org) 3.12+

### 1. Clone o repositório

```bash
git clone https://github.com/[org]/sigi.git
cd sigi
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

### 3. Suba os containers

```bash
docker compose up --build
```

### 4. Execute as migrações

```bash
docker compose exec backend alembic upgrade head
```

---

## Contribuição

Contribuições são bem-vindas! Siga os passos abaixo:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/minha-feature`)
3. Commit suas alterações (`git commit -m 'feat: minha feature'`)
4. Faça o push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

**Isaac Kleimmann Graper** · 2026
