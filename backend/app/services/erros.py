"""Domain exceptions.

Services raise these; `app/api/erros.py` maps them to the envelope in
`api-conventions.md`. `CLAUDE.md` forbids raising `HTTPException` below the API
layer, which is what keeps the domain rules testable without a request.
"""

from __future__ import annotations


class ErroDominio(Exception):
    """Base for anything a caller did wrong.

    `codigo` is stable and machine-readable; `mensagem` is pt-BR, addressed to a
    servidor, and says what to do next. `campos` drives inline field errors — a
    single generic "dados inválidos" defeats the whole point, which is mitigating
    the transcription errors that motivated the project.
    """

    codigo: str = "ERRO_DOMINIO"
    http: int = 422

    def __init__(
        self,
        mensagem: str,
        *,
        campos: dict[str, str] | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campos = campos or {}
        # Seconds for a `Retry-After` header. A 429 whose only statement of
        # "when" is inside a pt-BR sentence is a 429 no client can obey.
        self.retry_after = retry_after


class CredenciaisInvalidas(ErroDominio):
    """Wrong password, unknown e-mail, or an address off the allowlist.

    One class for all three on purpose: AC-0001-02 requires the three responses
    to be byte-identical, and having separate classes is how they drift apart.
    """

    codigo = "CREDENCIAIS_INVALIDAS"
    http = 401

    def __init__(self) -> None:
        super().__init__("E-mail ou senha inválidos.")


class UsuarioInativo(ErroDominio):
    codigo = "USUARIO_INATIVO"
    http = 401

    def __init__(self) -> None:
        super().__init__("Esta conta não está ativa. Procure o gestor da sua unidade.")


class PerfilNaoAutorizado(ErroDominio):
    """Authenticated, and the profile does not permit it (RN04, A01).

    403 rather than 404 on purpose: the caller is a known servidor of the
    entity, and hiding that the action exists would only make them ask a
    colleague to try it too.
    """

    codigo = "PERFIL_NAO_AUTORIZADO"
    http = 403

    def __init__(self) -> None:
        super().__init__("Seu perfil não permite esta ação.")


class RefreshInvalido(ErroDominio):
    codigo = "REFRESH_INVALIDO"
    http = 401

    def __init__(self) -> None:
        super().__init__("Sua sessão não é mais válida. Entre novamente.")


class RotaIndisponivel(ErroDominio):
    """A mechanism switched off by configuration (AC-0001-24).

    404 rather than 403: a mechanism that is off should be indistinguishable
    from one that was never built.
    """

    codigo = "NAO_ENCONTRADO"
    http = 404

    def __init__(self) -> None:
        super().__init__("Recurso não encontrado.")


class TentativasExcedidas(ErroDominio):
    """The address is locked after repeated failures (AC-0001-03).

    429 rather than 401: the caller is not being told their credential is
    wrong — this attempt was never evaluated.
    """

    codigo = "TENTATIVAS_EXCEDIDAS"
    http = 429

    def __init__(self, *, minutos: int) -> None:
        super().__init__(
            f"Muitas tentativas. Tente novamente em {minutos} minutos.",
            retry_after=minutos * 60,
        )


class UsuarioNaoEncontrado(ErroDominio):
    """No usuario with that id, or none this caller may see.

    404 rather than 403 on the second case: telling an auditor that an id exists
    but is out of their scope leaks the existence of accounts by enumeration.
    """

    codigo = "NAO_ENCONTRADO"
    http = 404

    def __init__(self) -> None:
        super().__init__("Usuário não encontrado.")


class EmailJaCadastrado(ErroDominio):
    """The address already has an account, in any status (AC-0001-28).

    A second account for one person would split their audit trail in two, and
    neither half would answer "what did this person do".
    """

    codigo = "EMAIL_JA_CADASTRADO"
    http = 409

    def __init__(self) -> None:
        super().__init__(
            "Já existe uma conta para este e-mail. Se a pessoa esqueceu a senha, "
            "use 'redefinir senha' em vez de convidar de novo.",
            campos={"email": "Este e-mail já tem conta."},
        )


class DominioNaoInstitucional(ErroDominio):
    """The invited address is not on the institutional allowlist (AC-0001-28)."""

    codigo = "DOMINIO_NAO_INSTITUCIONAL"
    http = 422

    def __init__(self, dominios: list[str]) -> None:
        aceitos = ", ".join(dominios)
        super().__init__(
            f"Use um e-mail institucional. Domínios aceitos: {aceitos}.",
            campos={"email": f"Domínios aceitos: {aceitos}."},
        )


class ConviteJaUtilizado(ErroDominio):
    codigo = "CONVITE_JA_UTILIZADO"
    http = 409

    def __init__(self) -> None:
        super().__init__("Este convite já foi utilizado. Peça um novo ao gestor.")


class ConviteExpirado(ErroDominio):
    codigo = "CONVITE_EXPIRADO"
    http = 409

    def __init__(self) -> None:
        super().__init__("Este convite expirou. Peça um novo ao gestor.")


class SenhaFraca(ErroDominio):
    """The password is below the policy (AC-0001-26).

    422 and not 409: the request is well formed, the value is wrong, and the
    caller can fix it by typing a different one. The token survives — a typo
    must not burn an invitation and force the gestor to issue another.
    """

    codigo = "SENHA_FRACA"
    http = 422

    def __init__(self, minimo: int) -> None:
        super().__init__(
            f"A senha precisa ter ao menos {minimo} caracteres.",
            campos={"senha": f"Mínimo de {minimo} caracteres."},
        )


class UltimoGestor(ErroDominio):
    """The operation would leave the entity with no active gestor (AC-0001-29).

    Without this, two individually permitted actions leave nobody able to manage
    members — and since there is no self-registration (AC-0001-21), there is no
    way back in short of database access.
    """

    codigo = "ULTIMO_GESTOR"
    http = 409

    def __init__(self) -> None:
        super().__init__(
            "Esta é a única conta de gestor ativa. Promova outro gestor antes de "
            "bloquear ou desativar esta."
        )


class EstadoInvalido(ErroDominio):
    """The OIDC callback carries a state that was never issued, or has expired."""

    codigo = "ESTADO_INVALIDO"
    http = 401

    def __init__(self) -> None:
        super().__init__("A tentativa de entrada expirou. Comece novamente.")


class AssercaoInvalida(ErroDominio):
    """The provider's identity token did not verify (AC-0001-20)."""

    codigo = "ASSERCAO_INVALIDA"
    http = 401

    def __init__(self) -> None:
        super().__init__("Não foi possível validar a resposta do provedor.")


class UsuarioNaoProvisionado(ErroDominio):
    """The assertion verified, and no usuario matches it (AC-0001-21).

    403 and not 404: the caller authenticated against the tenant, so they exist
    as a person. What they lack is an account here, and saying so is what tells
    them to ask the gestor rather than retry.
    """

    codigo = "USUARIO_NAO_PROVISIONADO"
    http = 403

    def __init__(self) -> None:
        super().__init__("Seu acesso ainda não foi liberado. Procure o gestor da sua unidade.")
