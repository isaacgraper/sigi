"""Fixed values of the history reads (SPEC-0007)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# Every `entidade_tipo` a row is written with, so a filter on any other is a typo.
ENTIDADE_TIPOS: Final = frozenset(
    {
        "usuario",
        "rota",
        "ata",
        "fornecedor",
        "insumo",
        "grupo_material",
        "nota_empenho",
        "nota_fiscal",
        "relatorio",
        "notificacao",
    }
)

# ATA rows carry the item they touch under this key (SPEC-0003 §8).
ATA_ENTIDADE: Final = "ata"
NOTA_EMPENHO_ENTIDADE: Final = "nota_empenho"
NOTA_FISCAL_ENTIDADE: Final = "nota_fiscal"
ITEM_ATA_KEY: Final = "item_ata_id"

# The stage of the cycle a row belongs to (AC-0007-07).
ETAPA_ATA: Final = "ata"
ETAPA_ITEM_ATA: Final = "item_ata"
ETAPA_NOTA_EMPENHO: Final = "nota_empenho"
ETAPA_NOTA_FISCAL: Final = "nota_fiscal"

# Two rows written in the same instant read in the order of the cycle.
ETAPA_RANK: Final = MappingProxyType(
    {ETAPA_ATA: 0, ETAPA_ITEM_ATA: 1, ETAPA_NOTA_EMPENHO: 2, ETAPA_NOTA_FISCAL: 3}
)

# Filter messages, pt-BR, because the auditor reads them under the input.
PERIODO_INVERTIDO: Final = "A data inicial deve ser anterior ou igual à final."
ENTIDADE_SEM_TIPO: Final = "Informe o tipo da entidade."
TIPO_DESCONHECIDO: Final = "Tipo de entidade desconhecido."

# ── What each event changed (AC-0007-10) ────────────────────────────────────

# The subject of an ATA row that touches one of its items, walked on its own.
ITEM_ATA_ENTIDADE: Final = "item_ata"
GRUPO_MATERIAL_ENTIDADE: Final = "grupo_material"
INSUMO_ENTIDADE: Final = "insumo"

# The kind of each aditivo whose acréscimo makes the "after" of its row.
ADITIVO_ACAO: Final = "ata.aditivo_registrado"
ADITIVO_VALOR: Final = "valor"
ADITIVO_QUANTIDADE: Final = "quantidade"

# How the screen formats a value; the list is closed by SPEC-0007 §2.1.
TIPO_DATA: Final = "data"
TIPO_DINHEIRO: Final = "dinheiro"
TIPO_QUANTIDADE: Final = "quantidade"
TIPO_TEXTO: Final = "texto"
TIPO_STATUS: Final = "status"
TIPO_REFERENCIA: Final = "referencia"
TIPO_ITENS: Final = "itens"
# Compared as numbers, so "10.00" and "10" are the same value.
NUMERIC_TIPOS: Final = frozenset({TIPO_DINHEIRO, TIPO_QUANTIDADE})

# The fields of each entity a row can change, keyed by column: (label, type).
# `valor_contratado` and `quantidade_contratada` are not columns: an aditivo
# records them as the total before its acréscimo (SPEC-0002, SPEC-0003).
FIELDS: Final = MappingProxyType(
    {
        ATA_ENTIDADE: MappingProxyType(
            {
                "numero": ("Número", TIPO_TEXTO),
                "objeto": ("Objeto", TIPO_TEXTO),
                "orgao": ("Órgão", TIPO_TEXTO),
                "fornecedor_id": ("Fornecedor", TIPO_REFERENCIA),
                "data_emissao": ("Data de emissão", TIPO_DATA),
                "vigencia_inicio": ("Início da vigência", TIPO_DATA),
                "vigencia_fim": ("Fim da vigência", TIPO_DATA),
                "valor_total": ("Valor total", TIPO_DINHEIRO),
                "data_orcamento_planilhado": ("Data do orçamento planilhado", TIPO_DATA),
                "status": ("Status", TIPO_STATUS),
                "responsavel_id": ("Responsável", TIPO_REFERENCIA),
                "valor_contratado": ("Valor contratado", TIPO_DINHEIRO),
            }
        ),
        ITEM_ATA_ENTIDADE: MappingProxyType(
            {
                "numero_item": ("Número do item", TIPO_TEXTO),
                "insumo_id": ("Insumo", TIPO_REFERENCIA),
                "fornecedor_id": ("Fornecedor", TIPO_REFERENCIA),
                "quantidade": ("Quantidade", TIPO_QUANTIDADE),
                "valor_unitario": ("Valor unitário", TIPO_DINHEIRO),
                "quantidade_contratada": ("Quantidade contratada", TIPO_QUANTIDADE),
            }
        ),
        INSUMO_ENTIDADE: MappingProxyType(
            {
                "sku": ("SKU", TIPO_TEXTO),
                "descricao": ("Descrição", TIPO_TEXTO),
                "unidade": ("Unidade", TIPO_TEXTO),
                "grupo_id": ("Grupo", TIPO_REFERENCIA),
                "codigo_doms": ("Código DOMS", TIPO_TEXTO),
                "codigo_externo": ("Código externo", TIPO_TEXTO),
                "quantidade_referencia": ("Quantidade de referência", TIPO_QUANTIDADE),
                "substituido_por_id": ("Substituído por", TIPO_REFERENCIA),
                "descontinuado_em": ("Descontinuado em", TIPO_DATA),
            }
        ),
        GRUPO_MATERIAL_ENTIDADE: MappingProxyType(
            {
                "nome": ("Nome", TIPO_TEXTO),
                "nivel": ("Nível", TIPO_TEXTO),
                "parent_id": ("Grupo superior", TIPO_REFERENCIA),
            }
        ),
        NOTA_EMPENHO_ENTIDADE: MappingProxyType(
            {
                "processo_sei": ("Processo SEI", TIPO_TEXTO),
                "ata_id": ("ATA", TIPO_REFERENCIA),
                "status": ("Etapa", TIPO_STATUS),
                "numero_pre_empenho": ("Número do pré-empenho", TIPO_TEXTO),
                "numero": ("Número da NE", TIPO_TEXTO),
                "data_emissao": ("Data de emissão", TIPO_DATA),
                "responsavel_id": ("Responsável", TIPO_REFERENCIA),
                "itens": ("Itens", TIPO_ITENS),
            }
        ),
        NOTA_FISCAL_ENTIDADE: MappingProxyType(
            {
                "numero": ("Número da NF", TIPO_TEXTO),
                "data_emissao": ("Data de emissão", TIPO_DATA),
                "valor": ("Valor", TIPO_DINHEIRO),
                "nota_empenho_id": ("NE", TIPO_REFERENCIA),
                "fornecedor_id": ("Fornecedor", TIPO_REFERENCIA),
                "status": ("Status", TIPO_STATUS),
                "justificativa_devolucao": ("Justificativa da devolução", TIPO_TEXTO),
                "quarentena": ("Em quarentena", TIPO_STATUS),
                "motivo_quarentena": ("Motivo da quarentena", TIPO_TEXTO),
                "responsavel_id": ("Responsável", TIPO_REFERENCIA),
                "itens": ("Itens", TIPO_ITENS),
            }
        ),
    }
)

# The key that identifies a line inside each entity's `itens`.
ITEM_LINE_KEY: Final = MappingProxyType(
    {NOTA_EMPENHO_ENTIDADE: "item_ata_id", NOTA_FISCAL_ENTIDADE: "item_nota_empenho_id"}
)
ITEM_QUANTIDADE_KEY: Final = "quantidade"
ITENS_KEY: Final = "itens"
STATUS_KEY: Final = "status"

# The label of every recorded key that is not a field of its entity.
DETALHE_ROTULO: Final = MappingProxyType(
    {
        "item_ata_id": "Item da ATA",
        "sku": "SKU",
        "substituto": "Substituto",
        "grupos": "Grupos",
        "valor_reservado_ata": "Valor reservado na ATA",
        "valor_liberado": "Valor liberado",
        "saldo_disponivel": "Saldo disponível",
        "motivo": "Motivo",
        "justificativa": "Justificativa",
        "confirmar_data_anterior": "Data anterior ao empenho confirmada",
        "status": "Status",
        "perfil": "Perfil",
        "mecanismo": "Mecanismo",
        "alvo_id": "Membro",
        "sessoes_revogadas": "Sessões revogadas",
        "tentativas": "Tentativas",
        "rota": "Rota",
        "metodo": "Método",
        "origem_hmac": "Origem (HMAC)",
        "institucional": "Rede institucional",
        "email_hmac": "E-mail (HMAC)",
        "dominio": "Domínio",
        "relatorio": "Relatório",
        "formato": "Formato",
        "referencia": "Data de referência",
        "ata_id": "ATA",
        "inicio": "Início do período",
        "colunas": "Colunas",
        "chave": "Chave",
        "lidas": "Lidos",
        "avisos": "Avisos",
        "destinatarios": "Destinatários",
        "erro": "Erro",
        "filtros": "Filtros",
    }
)

# The pt-BR label of each acao; one missing reads as the acao itself.
ACAO_ROTULO: Final = MappingProxyType(
    {
        "ata.criada": "ATA registrada",
        "ata.editada": "ATA corrigida",
        "ata.suspensa": "ATA suspensa",
        "ata.retomada": "ATA retomada",
        "ata.encerrada": "ATA encerrada",
        "ata.cancelada": "ATA cancelada",
        "ata.aditivo_registrado": "Aditivo registrado",
        "ata.reajuste_registrado": "Pedido de reajuste registrado",
        "ata.item_adicionado": "Item adicionado",
        "ata.item_editado": "Item corrigido",
        "ata.item_removido": "Item removido",
        "insumo.criado": "Insumo cadastrado",
        "insumo.editado": "Insumo corrigido",
        "insumo.sku_alterado": "SKU alterado",
        "insumo.descontinuado": "Insumo descontinuado",
        "insumo.substituido": "Insumo substituído",
        "insumo.reativado": "Insumo reativado",
        "grupo_material.criado": "Grupo cadastrado",
        "grupo_material.editado": "Grupo renomeado",
        "ne.criada": "NE criada",
        "ne.itens_alterados": "Itens da NE alterados",
        "ne.avancada": "NE avançou de etapa",
        "ne.revertida": "NE voltou de etapa",
        "ne.cancelada": "NE cancelada",
        "ne.bloqueada": "Avanço da NE recusado",
        "nf.registrada": "NF lançada",
        "nf.corrigida": "NF corrigida",
        "nf.enviada": "NF enviada à conferência",
        "nf.aprovada": "NF aprovada",
        "nf.devolvida": "NF devolvida",
        "nf.quarentena_iniciada": "NF em quarentena",
        "nf.quarentena_liberada": "NF liberada da quarentena",
        "relatorio.exportado": "Relatório exportado",
        "notificacao.criada": "Aviso de ATA criado",
        "notificacao.lida": "Aviso lido",
        "notificacao.todas_lidas": "Avisos marcados como lidos",
        "notificacao.enviada": "Resumo de avisos enviado",
        "notificacao.envio_falhou": "Envio do resumo de avisos falhou",
        "usuario.convidado": "Membro convidado",
        "usuario.convite_reemitido": "Convite reemitido",
        "usuario.ativado": "Conta ativada",
        "usuario.bloqueado": "Membro bloqueado",
        "usuario.desbloqueado": "Membro desbloqueado",
        "usuario.desativado": "Membro desativado",
        "usuario.gestor_inicial": "Primeiro gestor criado",
        "usuario.grupos_alterados": "Grupos do membro alterados",
        "usuario.redefinicao_solicitada": "Redefinição de senha solicitada",
        "usuario.redefinicao_concluida": "Senha redefinida",
        "usuario.semente_demonstracao": "Conta de demonstração criada",
        "usuario.ultimo_gestor": "Remoção do último gestor recusada",
        "auth.login": "Entrada no sistema",
        "auth.logout": "Saída do sistema",
        "auth.falha": "Entrada recusada",
        "auth.bloqueio_tentativas": "Bloqueio por tentativas",
        "auth.limite_excedido": "Limite de requisições excedido",
        "auth.negada": "Acesso negado",
        "auth.oidc_claim": "Entrada institucional",
        "auth.oidc_recusada": "Entrada institucional recusada",
        "auth.refresh_replay": "Reuso de sessão detectado",
    }
)

# Acoes whose row records no prior value: the fields the entity was created with.
CREATION_ACOES: Final = frozenset(
    {
        "ata.criada",
        "ata.item_adicionado",
        "insumo.criado",
        "grupo_material.criado",
        "ne.criada",
        "nf.registrada",
    }
)

# Acoes that end an entity, with the column the removal sets, cleared when rewound.
REMOVAL_ACOES: Final = MappingProxyType({"ata.item_removido": "removido_em"})

# Fields an acao sets without recording their prior value, by the status it
# moves to (`None` for any): the prior value is known, so it is not guessed.
IMPLIED_PRIOR: Final = MappingProxyType(
    {
        ("ne.avancada", "pre_empenho"): MappingProxyType({"numero_pre_empenho": None}),
        ("ne.avancada", "ne_emitida"): MappingProxyType({"numero": None, "data_emissao": None}),
        ("nf.devolvida", None): MappingProxyType({"justificativa_devolucao": None}),
        ("nf.quarentena_iniciada", None): MappingProxyType(
            {"quarentena": False, "motivo_quarentena": None}
        ),
        ("nf.quarentena_liberada", None): MappingProxyType({"quarentena": True}),
    }
)

# A recorded key that holds a field under another name.
RENAMED_KEY: Final = MappingProxyType({("nf.quarentena_liberada", "motivo"): "motivo_quarentena"})

# Keys recorded as the total before an acréscimo; the "after" adds it.
ACRESCIMO_KEYS: Final = frozenset({"valor_contratado", "quantidade_contratada"})

# Acoes that changed nothing: a refused move records the state it was refused in.
DETAILS_ONLY: Final = frozenset({"ne.bloqueada"})

# Columns that are bookkeeping, never a change a person made.
UNTRACKED_COLUMNS: Final = frozenset({"id", "criado_em", "atualizado_em"})

# A column read under another field name: the grupo's parent is `parent_id`
# in FIELDS, as SPEC-0003's API names it, and `grupo_pai_id` in the table.
STATE_KEY: Final = MappingProxyType({"grupo_pai_id": "parent_id"})

# The attribute of an aditivo holding the acréscimo of each kind; a prazo has none.
ACRESCIMO_ATTRIBUTE: Final = MappingProxyType(
    {ADITIVO_VALOR: "valor_acrescimo", ADITIVO_QUANTIDADE: "quantidade_acrescimo"}
)
