---
id: SPEC-0008
title: Notificações das ATAs
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF09, RF19]
depends_on: [SPEC-0002, SPEC-0006, SPEC-0011]
milestone: M4
---

# SPEC-0008 — Notificações das ATAs

## 1. Purpose

Say, without anyone having to look, which ATAs need attention: the ones about
to end, the ones that ended, the ones whose saldo is running out and the ones
whose reajuste is due. The product owner, on 2026-11-11: *"isso é rastreio de
ata, isso é para ver as atas, seu saldo e afins, perto do vencimento, venceram,
vão vencer"*.

The entity's TI blocks per-event e-mail as spam (17/08 meeting, §6), so nothing
here is sent per event: the system raises a notice once per ATA and per reason,
shows it under the bell, and gathers the day's new notices in one e-mail.

## 2. Scope

**In scope:** the notices of §3; the bell in the header and its list; marking
read; the daily e-mail digest behind a sending port, written to a local folder
outside production and sent only once an SMTP server is configured.

**Out of scope:** notices about NEs and NFs; what entered and left the critical
list, which waits for the coverage import (SPEC-0012); opting out, since the
digest is one e-mail a day at most.

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

**AC-0008-06** — The daily digest
```gherkin
Given members with notices raised since the last digest
When  the daily check runs
Then  every active member receives one e-mail at the address they sign in with, listing them, grouped by reason, with a link to each ATA
And   a day with nothing new sends none
```

**AC-0008-07** — No SMTP, no send
```gherkin
Given no SMTP server configured, or APP_ENV other than production
When  the digest is built
Then  it is written to a local folder and no external connection is opened
And   the notices in the bell are unaffected
```

**AC-0008-08** — A failed send is recorded
```gherkin
Given an SMTP server that refuses or does not answer
When  the digest is sent
Then  the failure is recorded in the history, the notices stay in the bell
And   the next day's digest carries them again
```
There is no queue and no retry loop (AC-0009-07 withdrawn on 2026-11-10): the
next run is the retry.

**AC-0008-09** — Nothing personal
```gherkin
Given a digest
Then  it names only its recipient, by name, and holds no CPF, SIAPE or other
      member's e-mail (RNF07)
```

## 4. Permissions

Every signed-in member reads the notices and marks them read; the same for every
perfil. What one member has read does not change what another sees. The daily
check runs from the command line, not from an endpoint.

## 5. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| GET | `/api/v1/notificacoes` | The notices, newest first, paginated, with the member's unread count | 04 |
| POST | `/api/v1/notificacoes/{id}/lida` | Mark one read | 05 |
| POST | `/api/v1/notificacoes/lidas` | Mark all read | 05 |

`python -m app.cli notificar` runs the check and the digest; the server's
scheduler runs it once a day.

## 6. Implementation plan

1. Migration `0008_notificacoes`: `notificacao` (the ATA, the reason, the key
   that makes it once per ATA and reason, when raised) and
   `notificacao_leitura` (which member read which notice, and when), and when
   each digest went out.
2. `app/services/notificacoes.py`: the check over the ATAs with SPEC-0002's and
   SPEC-0006's reads, the digest, and the reads and marks.
3. `app/services/mail.py`: the `NotificationSender` port, a folder adapter and an
   SMTP adapter on the standard library; settings `smtp_host`, `smtp_port`,
   `smtp_from`, `mail_folder`.
4. The routes, the CLI command, and a `notificacao.lida` and
   `notificacao.enviada` row in the history for each write.
5. Frontend: the bell in the header (`components/shell`), its list and marks.
6. Tests per AC in `tests/test_notificacoes.py` and `frontend/e2e/notificacoes.spec.ts`.

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
