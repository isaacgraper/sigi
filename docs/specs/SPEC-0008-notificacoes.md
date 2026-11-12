---
id: SPEC-0008
title: Notificações e resumo por e-mail
status: Approved
version: 1.1
owner: Isaac Kleimmann Graper
satisfies: [RF09, RF19]
depends_on: [SPEC-0002, SPEC-0004, SPEC-0005, SPEC-0006, SPEC-0011]
milestone: M4
---

# SPEC-0008 — Notificações e resumo por e-mail

## 1. Purpose

Say, without anyone having to look, which ATAs need attention: the ones about
to end, the ones that ended, the ones whose saldo is running out and the ones
whose reajuste is due. The product owner, on 2026-11-11: *"isso é rastreio de
ata, isso é para ver as atas, seu saldo e afins, perto do vencimento, venceram,
vão vencer"*.

The entity's TI blocks per-event e-mail as spam (17/08 meeting, §7), so nothing
here is sent per event. The bell is the platform's ordinary notification bell.
The e-mail is a summary on a fixed template, built on the application server
with the system's data of that day, daily or weekly as each member chooses
(product owner, 2026-11-12).

## 2. Scope

**In scope:** the notices of §3 and the bell in the header; marking read; the
e-mail summary of ATAs, NEs and NFs on a fixed template; each member's choice of
daily, weekly on a weekday, or none; the summary written to a local folder
outside production and sent only once an SMTP server is configured.

**Out of scope:** what entered and left the critical list, which waits for the
coverage import (SPEC-0012); a template the entity edits.

## 3. Behaviour

**AC-0008-01** — The reasons for a notice
```gherkin
Given an ATA
When  the daily check runs
Then  a notice is raised for it when its vigência ends within 90 days with no
      aditivo de prazo ("vai vencer"), when its vigência has ended ("venceu"),
      when its saldo reaches the alto consumo of SPEC-0006 ("saldo em 80%"),
      when its saldo disponível reaches zero ("saldo esgotado"), or when its
      reajuste is due with no request (AC-0002-20, "reajuste a pedir")
```
The 90 days and the 80% are the ones SPEC-0002 and SPEC-0006 already use.

**AC-0008-02** — Once per ATA and reason
```gherkin
Given an ATA with a notice for a reason
When  the daily check runs again and the reason still holds
Then  no second notice is raised for it
And   a new vigência, a new aditivo or a reajuste requested lets the reason be raised again
```

**AC-0008-03** — The same notices for everyone
```gherkin
Given a notice
Then  every active member sees it, whatever the perfil
```
The product owner, on 2026-11-12: gestor, servidor and auditor are told the same
thing, and *"todo mundo que entrar na plataforma pelo email vai receber a
notificação naquele email cadastrado, e é só isso"*. A deactivated or blocked
member cannot sign in, so is told nothing.

**AC-0008-04** — The bell
```gherkin
Given a signed-in member with unread notices
Then  the bell in the header shows how many
When  it is opened
Then  the notices show newest first, each with the ATA, the reason and the day,
      and each opens the ATA's page
```

**AC-0008-05** — Read
```gherkin
Given the bell open
When  a notice is opened, or "Marcar todas como lidas" is pressed
Then  it is read for that member only, and the count falls
```

**AC-0008-06** — The summary
```gherkin
Given a member whose e-mail is due
When  the daily run reaches them
Then  they receive one e-mail at the address they sign in with, on the fixed
      template, with the system's data of that day:
      the ATAs that will vencer, that venceram, with saldo at 80%, with saldo
      esgotado and with reajuste a pedir, each by its número;
      how many NEs are in each etapa, and how many advanced since their last summary;
      how many NFs are in conferência, devolvidas and em quarentena
And   each ATA links to its page
```

**AC-0008-07** — Each member's choice
```gherkin
Given a signed-in member on "Configurações"
When  they choose the e-mail daily, weekly on a weekday, or none, and save
Then  the summary follows that choice from the next run
And   a member who never chose receives it weekly, on Mondays
And   "none" stops the e-mail and leaves the bell as it is
```
The product owner, on 2026-11-12: *"vamos ter que criar a configuração de
usuário, para incluir esse tipo de informação"*.

**AC-0008-08** — When an e-mail is due
```gherkin
Given the daily run
Then  a daily member's summary is due every day
And   a weekly member's is due on their weekday, or on any later day when the
      last one is more than seven days old
And   a member's summary sent today is not sent twice
```
The second rule is what retries a weekly summary whose day failed.

**AC-0008-09** — No SMTP, no send
```gherkin
Given no SMTP server configured, or APP_ENV other than production
When  the summary is built
Then  it is written to a local folder and no external connection is opened
```

**AC-0008-10** — A failed send is recorded
```gherkin
Given an SMTP server that refuses or does not answer
When  a member's summary is sent
Then  the failure is recorded in the history and their last summary is not moved
And   the next run sends it again
```
There is no queue and no retry loop (AC-0009-07 withdrawn on 2026-11-10): the
next run is the retry.

**AC-0008-11** — Nothing personal
```gherkin
Given a summary
Then  it names only its recipient, by name, and holds no CPF, SIAPE or other
      member's e-mail (RNF07)
```

## 4. Permissions

Every signed-in member reads the notices, marks them read and sets their own
e-mail choice; the same for every perfil. What one member reads or chooses does
not change another's. The daily run is a command, not an endpoint.

## 5. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| GET | `/api/v1/notificacoes` | The notices, newest first, paginated, with the member's unread count | 04 |
| POST | `/api/v1/notificacoes/{id}/lida` | Mark one read | 05 |
| POST | `/api/v1/notificacoes/lidas` | Mark all read | 05 |
| GET | `/api/v1/preferencias/email` | The member's e-mail choice | 07 |
| PUT | `/api/v1/preferencias/email` | Set it: `frequencia` (`diario`, `semanal`, `nenhum`) and `dia_semana` (1 Monday to 7 Sunday) | 07 |

`python -m app.cli notificar` raises the notices and sends the summaries that
are due; the server's scheduler runs it once a day.

## 6. Implementation plan

1. Migration `0008_notificacoes`: `notificacao` (the ATA, the reason, the key
   that makes it once per ATA and reason, when raised), `notificacao_leitura`
   (which member read which notice, and when) and `preferencia_email` (each
   member's frequency, weekday and last summary).
2. `app/services/notificacoes.py`: the check over the ATAs with SPEC-0002's and
   SPEC-0006's reads, the reads and marks of the bell.
3. `app/services/resumo.py`: the day's data, the fixed template, which members
   are due, and the send.
4. `app/services/mail.py`: the `NotificationSender` port, a folder adapter and an
   SMTP adapter on the standard library; settings `smtp_host`, `smtp_port`,
   `smtp_starttls`, `smtp_username`, `smtp_password`, `smtp_from`, `mail_folder`.
5. The routes, the CLI command, and a history row for each write:
   `notificacao.criada`, `.lida`, `.todas_lidas`, `preferencia_email.alterada`,
   `resumo.enviado`, `resumo.envio_falhou`.
6. Frontend: the bell in the header (`components/shell`), "Configurações" in the
   user menu at `/configuracoes`, with the e-mail choice.
7. Tests per AC in `tests/test_notificacoes.py`, `tests/test_resumo.py`,
   `frontend/e2e/notificacoes.spec.ts` and `frontend/e2e/configuracoes.spec.ts`.

No new dependency: `smtplib` and `email` are the standard library's.

## 7. The 17/08 meeting

The entity's TI: *"e-mail demais, eles vão bloquear por spam. A gente tem que
ser mais cauteloso — escolher as coisas que realmente são extremamente
[importantes]"*. Hence one notice per ATA and reason, and one digest a day.

## 8. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF09, §5.1 |
| 0.2 | 2026-09-02 | Recorded the IT spam-block constraint from the 17/08 meeting: RF09 needs aggregated, threshold-driven digests per comprador, not per-event e-mail |
| 0.3 | 2026-11-11 | Rewritten by the product owner's answers on 2026-11-11: notices are about ATAs (vai vencer, venceu, saldo em 80%, saldo esgotado, reajuste a pedir), once per ATA and reason; the bell now and a daily digest by e-mail behind a port, sent once SMTP exists (OQ-13); a scheduled command, no queue; the same notices for every perfil. Per-event e-mail on NE transitions, the retry loop and the opt-out are withdrawn |
| 1.0 | 2026-11-12 | Approved by the product owner: every member is told the same, and the digest goes to the e-mail each signs in with, "e é só isso". No perfil sees a different set |
| 1.1 | 2026-11-12 | Product owner, 2026-11-12: the bell is the platform's ordinary bell; the e-mail is a summary on a fixed template with the system's data of that day (ATAs, NEs and NFs), daily or weekly as each member chooses on "Configurações", or none. AC-0008-06 to -11 replace the digest of new notices |
