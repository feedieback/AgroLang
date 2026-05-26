"""
================================================================================
AgroLang IDE
================================================================================
Compilador completo de uma Linguagem de Domínio Específico (DSL) para automação
de regras de manejo agrícola, integrado a uma interface gráfica de desenvolvimento
(IDE) construída com Tkinter.

Arquitetura em cinco módulos sequenciais:
    1. Análise Léxica   — tokenização do código-fonte (PLY Lex)
    2. Análise Sintática — construção da AST           (PLY LALR Parser)
    3. Análise Semântica — validação de coerência lógica
    4. Gerador de Código — serialização da AST para JSON
    5. Interface Gráfica — IDE com 4 abas (Tkinter)

Dependências externas:
    pip install ply          (análise léxica e sintática)
    tkinter                  (já incluso no Python padrão)

Uso:
    python N2.py

Autor  : Victor Augusto de Oliveira
Curso  : Engenharia da Computação — FHO Fundação Herminio Ometto
================================================================================
"""

# ── Biblioteca padrão ─────────────────────────────────────────────────────────
import json                             # Serialização do JSON de saída
import tkinter as tk                    # Janela principal e widgets base
from tkinter import ttk, scrolledtext, messagebox   # Abas, editor, diálogos
import re                               # Expressões regulares para o highlight

# ── Dependência externa ───────────────────────────────────────────────────────
import ply.lex  as lex                  # Gerador de analisador léxico
import ply.yacc as yacc                 # Gerador de parser LALR(1)


# ==============================================================================
# MÓDULO 1 — ANÁLISE LÉXICA (Scanner / Lexer)
# ==============================================================================
#
# Responsabilidade: transformar o código-fonte AgroLang (uma string) em uma
# sequência de tokens tipados. Cada token carrega: tipo, valor e número de linha.
#
# O PLY reconhece regras léxicas de duas formas:
#   • Variáveis de módulo t_NOME = r'regex'  → simples, sem ação
#   • Funções def t_NOME(t): r'regex' ...    → com ação (maior prioridade)
#
# Prioridade de reconhecimento (PLY):
#   1. Funções (por comprimento da regex, mais longa primeiro)
#   2. Variáveis (por comprimento da string, mais longa primeiro)
# ==============================================================================

# ------------------------------------------------------------------------------
# Conjunto de variáveis válidas
# ------------------------------------------------------------------------------
# Contém os identificadores de sensores mapeados ao hardware físico do sistema
# de monitoramento. Qualquer variável usada em uma condição AgroLang deve
# pertencer a este conjunto — verificado pelo Módulo 3 (análise semântica).
#
# Módulo 1 — Sensores de solo, ar e ambiente (ESP32 + sensores analógicos)
# Módulo 2 — Visão computacional (câmera + YOLOv8)
VARIAVEIS_NUMERICAS = {
    'umidade_solo',     # % de umidade do solo          (Módulo 1 - Solo)
    'umidade_ar',       # % de umidade relativa do ar   (Módulo 1 - Ar)
    'temperatura_ar',   # Temperatura do ar em °C        (Módulo 1 - Ar)
    'temperatura_solo', # Temperatura do solo em °C      (Módulo 1 - Solo)
    'contagem_pragas',  # Nº de pragas detectadas        (Módulo 2 - Visão)
    'indice_saude',     # Índice de saúde foliar 0-100   (Módulo 2 - Visão)
    'luminosidade',     # Intensidade luminosa em lux    (Módulo 1 - Ambiente)
    'ph_solo',          # pH do solo                     (Módulo 1 - Solo)
    'nivel_agua',       # Nível do reservatório          (Módulo 1 - Solo)
}

# ------------------------------------------------------------------------------
# Palavras reservadas da linguagem
# ------------------------------------------------------------------------------
# Mapeamento de lexema → tipo de token. Consultado dentro de t_IDENTIFICADOR
# para reclassificar tokens genéricos que coincidam com palavras da linguagem.
# Dessa forma, um identificador como "SE_VALOR" não é confundido com a palavra
# reservada "SE", pois o padrão r'[a-zA-Z_][a-zA-Z0-9_]*' captura o nome completo.
reserved = {
    'REGRA': 'REGRA',   # Abre a declaração de uma regra
    'SE':    'SE',      # Inicia a condição de uma regra
    'ENTAO': 'ENTAO',   # Inicia a ação principal
    'SENAO': 'SENAO',   # Inicia a ação alternativa (opcional)
    'E':     'E',       # Operador lógico AND
    'OU':    'OU',      # Operador lógico OR
}

# ------------------------------------------------------------------------------
# Lista de todos os tipos de tokens reconhecidos pelo lexer
# ------------------------------------------------------------------------------
# Exigida pelo PLY com este nome exato. Todos os tokens declarados aqui devem
# ter uma regra correspondente (variável t_* ou função t_*).
tokens = [
    # Identificadores e literais
    'IDENTIFICADOR',    # Nome de variável de sensor
    'NUMERO',           # Literal numérico inteiro ou decimal
    'STRING',           # Literal de texto entre aspas duplas

    # Operadores relacionais
    'MAIOR',            # >
    'MENOR',            # <
    'IGUAL',            # ==
    'MAIOR_IGUAL',      # >=
    'MENOR_IGUAL',      # <=
    'DIFERENTE',        # !=

    # Delimitadores estruturais
    'LPAREN',           # (
    'RPAREN',           # )
    'LBRACE',           # {
    'RBRACE',           # }
    'PONTO_VIRGULA',    # ;

    # Funções de ação (tokens especiais com prioridade léxica)
    'DISPARAR_ALERTA',  # disparar_alerta(...)
    'IRRIGAR',          # irrigar(...)

] + list(reserved.values())  # Inclui REGRA, SE, ENTAO, SENAO, E, OU

# ------------------------------------------------------------------------------
# Regras léxicas simples (variáveis de módulo)
# ------------------------------------------------------------------------------
# Para tokens sem lógica de transformação, a regra é declarada como variável.
# O PLY ordena automaticamente pelo comprimento da regex (mais longa primeiro),
# garantindo que ">=" seja reconhecido antes de ">".

t_MAIOR         = r'>'        # Operador maior que
t_MENOR         = r'<'        # Operador menor que
t_IGUAL         = r'=='       # Operador de igualdade (dois sinais para distinguir de atribuição)
t_MAIOR_IGUAL   = r'>='       # Operador maior ou igual
t_MENOR_IGUAL   = r'<='       # Operador menor ou igual
t_DIFERENTE     = r'!='       # Operador de desigualdade
t_LPAREN        = r'\('       # Parêntese esquerdo (escapado na regex)
t_RPAREN        = r'\)'       # Parêntese direito (escapado na regex)
t_LBRACE        = r'\{'       # Chave esquerda (escapado na regex)
t_RBRACE        = r'\}'       # Chave direita (escapado na regex)
t_PONTO_VIRGULA = r';'        # Terminador de instrução / separador em irrigar()

# Caracteres ignorados silenciosamente pelo lexer (não geram token)
t_ignore = ' \t'              # Espaços e tabulações


# ------------------------------------------------------------------------------
# Regras léxicas com ação (funções)
# ------------------------------------------------------------------------------
# Funções t_* têm maior prioridade que variáveis t_*. Entre funções, o PLY
# ordena pelo comprimento da docstring (regex mais longa tem prioridade).
# Por isso, t_DISPARAR_ALERTA e t_IRRIGAR são declaradas ANTES de
# t_IDENTIFICADOR: sem isso, "disparar_alerta" seria capturado como
# IDENTIFICADOR genérico.

def t_DISPARAR_ALERTA(t):
    r'disparar_alerta'
    """
    Reconhece o token 'disparar_alerta'.

    Por ser uma função, tem prioridade sobre t_IDENTIFICADOR.
    Retorna o token sem modificação — o tipo já é DISPARAR_ALERTA
    pelo nome da função.

    Args:
        t: Objeto de token PLY com atributos .value, .type, .lineno.

    Returns:
        O próprio token t com type='DISPARAR_ALERTA'.
    """
    return t


def t_IRRIGAR(t):
    r'irrigar'
    """
    Reconhece o token 'irrigar'.

    Mesma estratégia de t_DISPARAR_ALERTA: prioridade garantida por ser função.

    Args:
        t: Objeto de token PLY.

    Returns:
        O próprio token t com type='IRRIGAR'.
    """
    return t


def t_IDENTIFICADOR(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    """
    Reconhece identificadores genéricos e palavras reservadas.

    O padrão captura qualquer sequência que começa com letra ou underscore,
    seguida de letras, dígitos ou underscores. Após o match, o dicionário
    'reserved' é consultado: se o lexema for uma palavra reservada, o tipo
    é sobrescrito; caso contrário, permanece 'IDENTIFICADOR'.

    Exemplos:
        'umidade_solo' → type='IDENTIFICADOR', value='umidade_solo'
        'SE'           → type='SE',            value='SE'
        'REGRA'        → type='REGRA',          value='REGRA'

    Args:
        t: Objeto de token PLY.

    Returns:
        Token com type ajustado (palavra reservada ou IDENTIFICADOR).
    """
    t.type = reserved.get(t.value, 'IDENTIFICADOR')
    return t


def t_NUMERO(t):
    r'\d+(\.\d+)?'
    """
    Reconhece literais numéricos inteiros ou decimais e converte o valor.

    O padrão r'\\d+(\\.\\d+)?' captura inteiros (ex: 30) e decimais (ex: 7.5).
    O valor é convertido para int se não houver ponto decimal, ou para float
    caso contrário. Essa conversão garante tipagem correta no JSON gerado.

    Exemplos:
        '30'  → value=30  (int)
        '7.5' → value=7.5 (float)

    Args:
        t: Objeto de token PLY.

    Returns:
        Token com value convertido para int ou float.
    """
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t


def t_STRING(t):
    r'\"([^\"\\]|\\.)*\"'
    """
    Reconhece literais de string entre aspas duplas e remove os delimitadores.

    O padrão aceita qualquer caractere exceto aspas não escapadas e barras
    invertidas soltas, além de sequências escapadas como \\" e \\\\. Após o
    match, as aspas delimitadoras são removidas via fatiamento [1:-1], de modo
    que o valor do token já contenha apenas o conteúdo da string.

    Exemplos:
        '"Setor A"'               → value='Setor A'
        '"ALTO RISCO: Praga!"'    → value='ALTO RISCO: Praga!'

    Args:
        t: Objeto de token PLY.

    Returns:
        Token com value sem aspas delimitadoras.
    """
    t.value = t.value[1:-1]
    return t


def t_newline(t):
    r'\n+'
    """
    Contabiliza quebras de linha para rastreamento de número de linha.

    Esta função NÃO retorna o token (não há 'return t'), portanto as quebras
    de linha são consumidas sem gerar token. O contador t.lexer.lineno é
    incrementado pelo número de '\\n' encontrados, mantendo a contagem correta
    para mensagens de erro com localização precisa.

    Args:
        t: Objeto de token PLY.
    """
    t.lexer.lineno += len(t.value)


def t_error(t):
    """
    Tratador de erros léxicos: chamado pelo PLY ao encontrar caractere inválido.

    Lança SyntaxError com prefixo [LÉXICO] informando o caractere problemático
    e o número da linha onde ele ocorre. Essa exceção interrompe a compilação
    imediatamente, sem tentar recuperação.

    Args:
        t: Objeto de token PLY com .value[0] = caractere inválido.

    Raises:
        SyntaxError: Sempre, com mensagem descritiva.
    """
    raise SyntaxError(
        f"[LÉXICO] Caractere inválido '{t.value[0]}' na linha {t.lexer.lineno}"
    )


# Instância global do lexer — compilada uma vez, reutilizada em todas chamadas.
# Em compilar(), uma segunda instância limpa é criada via lex.lex() para
# garantir estado inicial correto durante o parse.
lexer = lex.lex()


# ==============================================================================
# MÓDULO 2 — ANÁLISE SINTÁTICA (Parser)
# ==============================================================================
#
# Responsabilidade: verificar se a sequência de tokens obedece à gramática
# BNF da AgroLang e construir a Árvore Sintática Abstrata (AST).
#
# O PLY utiliza um parser LALR(1) gerado a partir das funções p_*.
# A docstring de cada função define uma ou mais produções BNF.
# O parâmetro 'p' é uma lista indexada:
#   p[0]  → valor do símbolo à esquerda da produção (resultado)
#   p[1], p[2], ... → valores dos símbolos à direita
#
# Gramática resumida:
#   programa       → lista_regras
#   lista_regras   → lista_regras regra | regra
#   regra          → REGRA string { SE condicao ENTAO acao [SENAO acao] }
#   condicao       → condicao E condicao | condicao OU condicao | id op_rel num
#   op_rel         → > | < | == | >= | <= | !=
#   acao           → disparar_alerta(string); | irrigar(string; numero);
# ==============================================================================

class NoAST:
    """
    Nó genérico da Árvore Sintática Abstrata (AST).

    Cada nó carrega um tipo (string identificadora) e atributos arbitrários
    definidos como kwargs. A abordagem com __dict__.update() elimina a
    necessidade de subclasses para cada tipo de nó, mantendo o código compacto.

    Tipos de nós criados pelo parser:
        'programa'              → atributos: regras (list)
        'regra'                 → atributos: nome, condicao, acao, acao_senao
        'condicao_logica'       → atributos: operador, esquerda, direita
        'condicao_simples'      → atributos: variavel, operador, valor
        'acao_disparar_alerta'  → atributos: mensagem
        'acao_irrigar'          → atributos: zona, duracao_minutos

    Exemplos:
        NoAST('regra', nome='Teste', condicao=..., acao=..., acao_senao=None)
        NoAST('condicao_simples', variavel='umidade_solo', operador='<', valor=30)
    """

    def __init__(self, tipo: str, **kwargs):
        """
        Inicializa o nó com tipo e atributos dinâmicos.

        Args:
            tipo:    String identificadora do tipo de nó.
            **kwargs: Atributos semânticos do nó (variam por tipo).
        """
        self.tipo = tipo
        self.__dict__.update(kwargs)   # Injeta os kwargs diretamente no objeto


# ------------------------------------------------------------------------------
# Produções gramaticais — nível 1: programa
# ------------------------------------------------------------------------------

def p_programa(p):
    """programa : lista_regras"""
    """
    Produção raiz da gramática.

    Um programa AgroLang é exatamente uma lista de uma ou mais regras.
    Cria o nó raiz da AST com o atributo 'regras' contendo a lista completa.

    p[1] = lista_regras (list de NoAST 'regra')
    p[0] = NoAST 'programa'
    """
    p[0] = NoAST('programa', regras=p[1])


# ------------------------------------------------------------------------------
# Produções gramaticais — nível 2: lista de regras (recursiva à esquerda)
# ------------------------------------------------------------------------------

def p_lista_regras_multiplas(p):
    """lista_regras : lista_regras regra"""
    """
    Caso recursivo: adiciona uma nova regra à lista existente.

    A recursividade à esquerda ('lista_regras regra' em vez de 'regra lista_regras')
    é preferida em parsers LALR pois evita conflitos de redução.

    p[1] = lista já construída (list)
    p[2] = nova regra (NoAST 'regra')
    p[0] = lista ampliada (list)
    """
    p[0] = p[1] + [p[2]]


def p_lista_regras_simples(p):
    """lista_regras : regra"""
    """
    Caso base: uma lista com exatamente uma regra.

    Encapsula o nó de regra em uma lista de um elemento, compatível com
    o tipo list esperado por p_programa e p_lista_regras_multiplas.

    p[1] = única regra (NoAST 'regra')
    p[0] = [p[1]] (list com um elemento)
    """
    p[0] = [p[1]]


# ------------------------------------------------------------------------------
# Produções gramaticais — nível 3: regra
# ------------------------------------------------------------------------------

def p_regra_com_senao(p):
    """regra : REGRA STRING LBRACE SE condicao ENTAO acao SENAO acao RBRACE"""
    """
    Regra com bloco SENAO obrigatório.

    Estrutura: REGRA "nome" { SE <cond> ENTAO <acao> SENAO <acao> }

    Índices na produção:
        p[1] = REGRA  (palavra reservada, descartada)
        p[2] = STRING (nome da regra, sem aspas)
        p[3] = {      (descartado)
        p[4] = SE     (descartado)
        p[5] = condicao (NoAST de condição)
        p[6] = ENTAO  (descartado)
        p[7] = acao   (NoAST de ação principal)
        p[8] = SENAO  (descartado)
        p[9] = acao   (NoAST de ação alternativa)
        p[10]= }      (descartado)

    Returns:
        NoAST 'regra' com acao_senao != None.
    """
    p[0] = NoAST('regra', nome=p[2], condicao=p[5], acao=p[7], acao_senao=p[9])


def p_regra_sem_senao(p):
    """regra : REGRA STRING LBRACE SE condicao ENTAO acao RBRACE"""
    """
    Regra sem bloco SENAO (comportamento padrão).

    Estrutura: REGRA "nome" { SE <cond> ENTAO <acao> }

    Índices na produção:
        p[2] = STRING (nome)
        p[5] = condicao
        p[7] = acao principal

    O atributo acao_senao é explicitamente definido como None, garantindo
    que o código consumidor possa sempre checar 'if regra.acao_senao' sem
    risco de AttributeError.

    Returns:
        NoAST 'regra' com acao_senao=None.
    """
    p[0] = NoAST('regra', nome=p[2], condicao=p[5], acao=p[7], acao_senao=None)


# ------------------------------------------------------------------------------
# Produções gramaticais — nível 4: condição
# ------------------------------------------------------------------------------

def p_condicao_binaria(p):
    """condicao : condicao E condicao
                | condicao OU condicao"""
    """
    Condição composta por dois predicados unidos com E (AND) ou OU (OR).

    Esta produção é recursiva: cada operando pode ser outra condição composta,
    permitindo encadeamentos arbitrários como:
        umidade_solo < 30 E temperatura_ar > 28 E luminosidade > 500

    Índices na produção:
        p[1] = condicao esquerda (NoAST)
        p[2] = operador ('E' ou 'OU')
        p[3] = condicao direita (NoAST)

    Returns:
        NoAST 'condicao_logica' com operador, esquerda e direita.
    """
    p[0] = NoAST('condicao_logica', operador=p[2], esquerda=p[1], direita=p[3])


def p_condicao_simples(p):
    """condicao : IDENTIFICADOR operador_rel NUMERO"""
    """
    Condição terminal: compara um sensor com um valor numérico literal.

    É o único tipo de condição que pode ser avaliado diretamente contra
    uma leitura de hardware. Exemplo: umidade_solo < 30

    Índices na produção:
        p[1] = IDENTIFICADOR (nome do sensor, ex: 'umidade_solo')
        p[2] = operador_rel  (string do operador, ex: '<')
        p[3] = NUMERO        (valor numérico, já convertido para int/float)

    Returns:
        NoAST 'condicao_simples' com variavel, operador e valor.
    """
    p[0] = NoAST('condicao_simples', variavel=p[1], operador=p[2], valor=p[3])


def p_operador_rel(p):
    """operador_rel : MAIOR
                    | MENOR
                    | IGUAL
                    | MAIOR_IGUAL
                    | MENOR_IGUAL
                    | DIFERENTE"""
    """
    Nó auxiliar que propaga o operador relacional como string.

    Cada alternativa produz simplesmente p[0] = p[1] (o lexema do token).
    Serve para que p_condicao_simples receba o operador já como string,
    sem precisar distinguir entre os 6 tipos de token de operador.

    Returns:
        String do operador: '>', '<', '==', '>=', '<=' ou '!='.
    """
    p[0] = p[1]


# ------------------------------------------------------------------------------
# Produções gramaticais — nível 5: ação
# ------------------------------------------------------------------------------

def p_acao_disparar(p):
    """acao : DISPARAR_ALERTA LPAREN STRING RPAREN PONTO_VIRGULA"""
    """
    Ação de notificação: publica mensagem no dashboard via MQTT.

    Sintaxe: disparar_alerta("mensagem");

    Índices na produção:
        p[1] = 'disparar_alerta'  (descartado)
        p[2] = '('                (descartado)
        p[3] = STRING             (mensagem, sem aspas — o lexer já removeu)
        p[4] = ')'                (descartado)
        p[5] = ';'                (descartado)

    Returns:
        NoAST 'acao_disparar_alerta' com atributo mensagem.
    """
    p[0] = NoAST('acao_disparar_alerta', mensagem=p[3])


def p_acao_irrigar(p):
    """acao : IRRIGAR LPAREN STRING PONTO_VIRGULA NUMERO RPAREN PONTO_VIRGULA"""
    """
    Ação de irrigação: aciona o relé do ESP32 por um período determinado.

    Sintaxe: irrigar("zona"; minutos);

    Nota sobre o separador ';': o ponto-e-vírgula foi escolhido intencionalmente
    como separador entre os argumentos (em vez de vírgula) para evitar conflito
    léxico com o ';' terminador de instrução ao final da ação.

    Índices na produção:
        p[1] = 'irrigar'   (descartado)
        p[2] = '('         (descartado)
        p[3] = STRING      (identificador da zona física, ex: 'Setor A')
        p[4] = ';'         (separador de argumentos — descartado)
        p[5] = NUMERO      (duração em minutos, já convertido para int/float)
        p[6] = ')'         (descartado)
        p[7] = ';'         (terminador de instrução — descartado)

    Returns:
        NoAST 'acao_irrigar' com atributos zona e duracao_minutos.
    """
    p[0] = NoAST('acao_irrigar', zona=p[3], duracao_minutos=p[5])


def p_error(p):
    """
    Tratador de erros sintáticos: chamado pelo PLY ao encontrar token inesperado.

    Lança SyntaxError com prefixo [SINTÁTICO]. Dois casos são tratados:
        - p não é None: token inesperado no meio do código (informa valor e linha).
        - p é None: fim de arquivo prematuro (o parser esperava mais tokens).

    Args:
        p: Objeto de token PLY (ou None em caso de EOF inesperado).

    Raises:
        SyntaxError: Sempre, com mensagem descritiva.
    """
    if p:
        raise SyntaxError(
            f"[SINTÁTICO] Token inesperado '{p.value}' na linha {p.lineno}"
        )
    else:
        raise SyntaxError("[SINTÁTICO] Fim de arquivo inesperado.")


# Instância global do parser LALR(1).
# Gerada uma única vez; as tabelas de parsing são calculadas pelo PLY
# a partir de todas as funções p_* declaradas acima.
parser = yacc.yacc()


# ==============================================================================
# MÓDULO 3 — ANÁLISE SEMÂNTICA
# ==============================================================================
#
# Responsabilidade: percorrer a AST já construída e validar invariantes que
# a gramática BNF não consegue expressar (coerência lógica, existência de
# variáveis no hardware, validade de parâmetros numéricos).
#
# Estratégia de acumulação: em vez de lançar exceção ao primeiro erro,
# todos os erros são coletados em self.erros e reportados de uma vez.
# Isso permite ao usuário corrigir múltiplos problemas em uma única compilação.
#
# Invariantes verificados:
#   S1 — Unicidade de nomes: nenhuma regra pode ter nome repetido no arquivo.
#   S2 — Integridade de variáveis: variáveis de condição ∈ VARIAVEIS_NUMERICAS.
#   S3 — Validade de parâmetros: duracao_minutos em irrigar() deve ser > 0.
# ==============================================================================

class AnalisadorSemantico:
    """
    Analisador semântico da AgroLang.

    Percorre a AST em profundidade e verifica três classes de invariantes
    semânticas. Os erros são acumulados em self.erros e reportados juntos
    ao final, sem interromper na primeira ocorrência.

    Uso:
        analisador = AnalisadorSemantico()
        analisador.analisar(ast)   # Lança ValueError se houver erros
    """

    def __init__(self):
        """Inicializa a lista de erros semânticos encontrados."""
        self.erros: list[str] = []

    def analisar(self, no: NoAST) -> None:
        """
        Ponto de entrada público da análise semântica.

        Itera sobre todas as regras do nó 'programa', verificando:
            (S1) Unicidade de nomes de regra.
            (S2) Integridade das variáveis em todas as condições.
            (S3) Validade dos parâmetros de todas as ações.

        Args:
            no: Nó raiz da AST (tipo='programa').

        Raises:
            ValueError: Se um ou mais erros semânticos forem detectados,
                        com todos os erros listados na mensagem.
        """
        nomes_vistos: list[str] = []   # Rastreia nomes para detectar duplicatas

        for regra in no.regras:
            # ── S1: Unicidade de nomes ────────────────────────────────────────
            if regra.nome in nomes_vistos:
                self.erros.append(f"Regra duplicada: '{regra.nome}'")
            nomes_vistos.append(regra.nome)

            # ── S2 + S3: Validação recursiva da condição e das ações ──────────
            self._analisar_condicao(regra.condicao)
            self._analisar_acao(regra.acao)

            # Bloco SENAO é opcional; só analisa se existir
            if regra.acao_senao is not None:
                self._analisar_acao(regra.acao_senao)

        # Reporta todos os erros acumulados de uma só vez
        if self.erros:
            raise ValueError(
                "[SEMÂNTICO] Erros encontrados:\n" +
                "\n".join(f"  - {e}" for e in self.erros)
            )

    def _analisar_condicao(self, no: NoAST) -> None:
        """
        Percorre recursivamente a árvore de condição verificando (S2).

        Para nós 'condicao_simples': verifica se a variável pertence a
        VARIAVEIS_NUMERICAS. Para nós 'condicao_logica': chama a si mesma
        nos filhos esquerdo e direito, cobrindo toda a árvore de predicados.

        Args:
            no: Nó de condição da AST ('condicao_simples' ou 'condicao_logica').
        """
        if no.tipo == 'condicao_simples':
            # S2 — Verifica se o identificador de sensor existe no hardware
            if no.variavel not in VARIAVEIS_NUMERICAS:
                self.erros.append(
                    f"Variável desconhecida: '{no.variavel}'. "
                    f"Válidas: {sorted(VARIAVEIS_NUMERICAS)}"
                )
        elif no.tipo == 'condicao_logica':
            # Percorre recursivamente ambos os lados da condição composta
            self._analisar_condicao(no.esquerda)
            self._analisar_condicao(no.direita)

    def _analisar_acao(self, no: NoAST) -> None:
        """
        Verifica invariantes semânticas de uma ação (S3).

        Apenas a ação 'acao_irrigar' possui restrição semântica: a duração
        deve ser estritamente positiva. Uma duração zero ou negativa poderia
        gerar ciclo indefinido de acionamento no relé do ESP32.

        A ação 'acao_disparar_alerta' não possui restrições além das já
        impostas pela gramática (argumento obrigatoriamente STRING).

        Args:
            no: Nó de ação da AST ('acao_disparar_alerta' ou 'acao_irrigar').
        """
        if no.tipo == 'acao_irrigar' and no.duracao_minutos <= 0:
            # S3 — Duração deve ser > 0 para proteger o atuador físico
            self.erros.append(
                f"Duração de irrigação inválida: {no.duracao_minutos} min "
                f"(deve ser > 0)."
            )


# ==============================================================================
# MÓDULO 4 — GERADOR DE CÓDIGO (AST → JSON)
# ==============================================================================
#
# Responsabilidade: serializar a AST validada em um dicionário Python que
# será convertido para JSON. O formato JSON foi escolhido por ser:
#   • Nativamente interpretável pelo servidor Apache (PHP)
#   • Consumível pela biblioteca ArduinoJson no firmware do ESP32
#   • Legível por humanos para depuração
#
# O campo "modulo" adicionado a cada nó de comparação é um metadado que
# permite ao dashboard web exibir a procedência física de cada variável
# sem consultas adicionais ao banco de dados.
# ==============================================================================

# Mapeamento de variável de sensor → nome do módulo físico de origem.
# Consultado por _condicao_para_dict para enriquecer o JSON com metadados.
MODULO_VARIAVEL: dict[str, str] = {
    'umidade_solo':     'Módulo 1 - Solo',
    'umidade_ar':       'Módulo 1 - Ar',
    'temperatura_ar':   'Módulo 1 - Ar',
    'temperatura_solo': 'Módulo 1 - Solo',
    'contagem_pragas':  'Módulo 2 - Visão Computacional',
    'indice_saude':     'Módulo 2 - Visão Computacional',
    'luminosidade':     'Módulo 1 - Ambiente',
    'ph_solo':          'Módulo 1 - Solo',
    'nivel_agua':       'Módulo 1 - Solo',
}


def _condicao_para_dict(no: NoAST) -> dict:
    """
    Serializa recursivamente um nó de condição da AST para dicionário Python.

    Dois tipos de nó são tratados:
        'condicao_simples'  → dict com tipo, variavel, modulo, operador, valor
        'condicao_logica'   → dict com tipo, operador, esquerda (recursivo), direita (recursivo)

    O campo 'modulo' em nós de comparação é um metadado derivado de
    MODULO_VARIAVEL, sem custo adicional de consulta em tempo de execução.

    Args:
        no: Nó de condição da AST.

    Returns:
        Dicionário Python representando a condição, pronto para json.dumps().

    Exemplos de saída:
        # condicao_simples
        {"tipo": "comparacao", "variavel": "umidade_solo",
         "modulo": "Módulo 1 - Solo", "operador": "<", "valor": 30}

        # condicao_logica
        {"tipo": "logica", "operador": "E",
         "esquerda": {...}, "direita": {...}}
    """
    if no.tipo == 'condicao_simples':
        return {
            "tipo":     "comparacao",
            "variavel": no.variavel,
            "modulo":   MODULO_VARIAVEL.get(no.variavel, 'Desconhecido'),
            "operador": no.operador,
            "valor":    no.valor,
        }
    # 'condicao_logica' → recursão nos filhos
    return {
        "tipo":     "logica",
        "operador": no.operador,
        "esquerda": _condicao_para_dict(no.esquerda),
        "direita":  _condicao_para_dict(no.direita),
    }


def _acao_para_dict(no: NoAST) -> dict:
    """
    Serializa um nó de ação da AST para dicionário Python.

    Dois tipos de nó são tratados:
        'acao_disparar_alerta' → {"tipo": "disparar_alerta", "mensagem": ...}
        'acao_irrigar'         → {"tipo": "irrigar", "zona": ..., "duracao_minutos": ...}

    Args:
        no: Nó de ação da AST.

    Returns:
        Dicionário Python representando a ação.
    """
    if no.tipo == 'acao_disparar_alerta':
        return {"tipo": "disparar_alerta", "mensagem": no.mensagem}
    # 'acao_irrigar'
    return {"tipo": "irrigar", "zona": no.zona, "duracao_minutos": no.duracao_minutos}


def gerar_json(ast: NoAST) -> dict:
    """
    Converte toda a AST em um dicionário Python estruturado.

    Itera sobre a lista de regras do nó raiz e serializa cada uma chamando
    _condicao_para_dict e _acao_para_dict. O campo 'senao' é None quando a
    regra não possui bloco SENAO — o campo é mantido explicitamente para que
    o consumidor (ESP32, PHP) não precise verificar ausência de chave.

    Args:
        ast: Nó raiz da AST (tipo='programa').

    Returns:
        Dict no formato:
        {
            "regras": [
                {
                    "nome": str,
                    "condicao": dict,
                    "entao": dict,
                    "senao": dict | None
                },
                ...
            ]
        }
    """
    resultado: dict = {"regras": []}

    for regra in ast.regras:
        resultado["regras"].append({
            "nome":     regra.nome,
            "condicao": _condicao_para_dict(regra.condicao),
            "entao":    _acao_para_dict(regra.acao),
            # None se não houver SENAO; preserva a chave para consumidores externos
            "senao":    _acao_para_dict(regra.acao_senao) if regra.acao_senao else None,
        })

    return resultado


def compilar(codigo_fonte: str) -> dict:
    """
    Ponto de entrada público do compilador AgroLang.

    Orquestra as quatro fases de compilação em sequência:
        1. Análise léxica   — alimenta o lexer e verifica erros léxicos
        2. Análise sintática — executa o parse e constrói a AST
        3. Análise semântica — valida invariantes lógicos da AST
        4. Geração de código — serializa a AST para dict/JSON

    Nota técnica: o lexer é alimentado duas vezes.
        Primeira vez  → list(lexer)  consome todos os tokens para
                        detectar erros léxicos antes do parse.
        Segunda vez   → lex.lex()    cria uma instância limpa (estado
                        zerado) para o parser, evitando que o lineno
                        acumulado da primeira passagem interfira nas
                        mensagens de erro do parser.

    Args:
        codigo_fonte: String contendo o programa AgroLang a compilar.

    Returns:
        Dicionário Python com as regras compiladas (equivalente ao JSON).

    Raises:
        SyntaxError: Em erros léxicos (prefixo [LÉXICO]) ou sintáticos
                     (prefixo [SINTÁTICO]).
        ValueError:  Em erros semânticos (prefixo [SEMÂNTICO]).

    Exemplo:
        resultado = compilar('REGRA "Teste" { SE umidade_solo < 30 ENTAO irrigar("A"; 10); }')
        # resultado == {"regras": [{"nome": "Teste", "condicao": {...}, "entao": {...}, "senao": None}]}
    """
    # Fase 1 — Léxica: verifica caracteres inválidos antes de qualquer parse
    lexer.input(codigo_fonte)
    list(lexer)                                         # Força consumo total

    # Fase 2 — Sintática: instância limpa do lexer para estado correto
    ast = parser.parse(codigo_fonte, lexer=lex.lex())

    # Fase 3 — Semântica: valida invariantes S1, S2 e S3
    AnalisadorSemantico().analisar(ast)

    # Fase 4 — Geração: serializa AST para dict
    return gerar_json(ast)


# ==============================================================================
# MÓDULO 5 — INTERFACE GRÁFICA (IDE)
# ==============================================================================
#
# Responsabilidade: fornecer uma interface de desenvolvimento integrado (IDE)
# para a linguagem AgroLang, construída sobre o framework Tkinter.
#
# Estrutura da janela:
#   ┌─────────────────────────────────────────────────┐
#   │  🌱 AgroLang IDE   (barra de título fixa)        │
#   ├──────────────┬──────────────┬────────────────────┤
#   │  🏠 Menu     │  🌿 Exemplos │  📖 Docs  │ ⌨️ Editor│
#   └──────────────┴──────────────┴────────────────────┘
#
# Tema visual: inspirado no editor "One Dark" (Atom/VS Code).
# Todas as cores são centralizadas no dicionário CORES abaixo.
# ==============================================================================

# ------------------------------------------------------------------------------
# Dados dos exemplos pré-definidos exibidos na aba "Exemplos"
# ------------------------------------------------------------------------------
# Cada entrada é um dict com três campos obrigatórios:
#   titulo    → exibido na Listbox lateral
#   descricao → exibido como subtítulo ao selecionar
#   codigo    → código AgroLang válido exibido no preview e carregado no editor
EXEMPLOS: list[dict] = [
    {
        "titulo": "1 — Alerta de Praga",
        "descricao": "Dispara alerta quando pragas e umidade do ar estão acima do limite.",
        "codigo": (
            'REGRA "Alerta de Praga" {\n'
            '    SE contagem_pragas > 30 E umidade_ar > 75\n'
            '    ENTAO disparar_alerta("ALTO RISCO: Mosca Branca detectada");\n'
            '}'
        ),
    },
    {
        "titulo": "2 — Irrigação Simples",
        "descricao": "Irriga o Setor A por 20 minutos quando a umidade do solo está baixa.",
        "codigo": (
            'REGRA "Irrigacao Simples" {\n'
            '    SE umidade_solo < 30\n'
            '    ENTAO irrigar("Setor A"; 20);\n'
            '}'
        ),
    },
    {
        "titulo": "3 — Irrigação com SENAO",
        "descricao": "Irriga se o solo estiver seco; caso contrário, emite alerta de solo adequado.",
        "codigo": (
            'REGRA "Controle de Irrigacao" {\n'
            '    SE umidade_solo < 30\n'
            '    ENTAO irrigar("Setor B"; 15);\n'
            '    SENAO disparar_alerta("Solo com umidade adequada");\n'
            '}'
        ),
    },
    {
        "titulo": "4 — Temperatura Crítica",
        "descricao": "Alerta quando temperatura ou índice de saúde da planta estão em estado crítico.",
        "codigo": (
            'REGRA "Temperatura Critica" {\n'
            '    SE temperatura_ar > 38 OU indice_saude < 40\n'
            '    ENTAO disparar_alerta("CRITICO: Estresse termico na lavoura");\n'
            '    SENAO disparar_alerta("Temperatura dentro do normal");\n'
            '}'
        ),
    },
    {
        "titulo": "5 — Múltiplas Regras",
        "descricao": "Irriga se solo seco e quente; alerta urgente se pragas elevadas.",
        "codigo": (
            'REGRA "Irrigacao Inteligente" {\n'
            '    SE umidade_solo < 25 E temperatura_ar > 32\n'
            '    ENTAO irrigar("Setor C"; 30);\n'
            '    SENAO disparar_alerta("Irrigacao nao necessaria");\n'
            '}\n\n'
            'REGRA "Praga Urgente" {\n'
            '    SE contagem_pragas > 50\n'
            '    ENTAO disparar_alerta("URGENTE: Aplicar defensivo agricola");\n'
            '}'
        ),
    },
]

# ------------------------------------------------------------------------------
# Texto de documentação exibido na aba "Documentação"
# ------------------------------------------------------------------------------
# String multi-linha formatada com caracteres Unicode de caixa.
# Exibida em ScrolledText somente leitura.
DOCUMENTACAO = """
╔══════════════════════════════════════════════════════════════╗
║           DOCUMENTAÇÃO DA LINGUAGEM AGROLANG                 ║
╚══════════════════════════════════════════════════════════════╝

━━━ ESTRUTURA BÁSICA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  REGRA "Nome da Regra" {
      SE <condição>
      ENTAO <ação>;
      SENAO <ação>;    ← opcional
  }

━━━ VARIÁVEIS DISPONÍVEIS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Variável             Módulo                    Descrição
  ─────────────────────────────────────────────────────────────
  umidade_solo         Módulo 1 - Solo           % de umidade do solo
  umidade_ar           Módulo 1 - Ar             % de umidade relativa do ar
  temperatura_ar       Módulo 1 - Ar             Temperatura do ar (°C)
  temperatura_solo     Módulo 1 - Solo           Temperatura do solo (°C)
  contagem_pragas      Módulo 2 - Visão Comp.    Nº de pragas detectadas
  indice_saude         Módulo 2 - Visão Comp.    Índice de saúde foliar (0-100)
  luminosidade         Módulo 1 - Ambiente       Nível de luminosidade (lux)
  ph_solo              Módulo 1 - Solo           pH do solo
  nivel_agua           Módulo 1 - Solo           Nível de água no reservatório

━━━ OPERADORES RELACIONAIS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  >    Maior que          <    Menor que
  >=   Maior ou igual     <=   Menor ou igual
  ==   Igual a            !=   Diferente de

━━━ OPERADORES LÓGICOS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  E    Conjunção (AND)    OU   Disjunção (OR)

  Exemplo: SE umidade_solo < 30 E temperatura_ar > 32

━━━ AÇÕES DISPONÍVEIS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. disparar_alerta("mensagem");
     → Envia notificação no dashboard web em tempo real.

  2. irrigar("zona"; minutos);
     → Ativa o sistema de irrigação na zona especificada
       pelo número de minutos indicado (deve ser > 0).

  Exemplos:
     ENTAO disparar_alerta("ALTO RISCO: Pragas detectadas");
     ENTAO irrigar("Setor A"; 20);

━━━ BLOCO SENAO (OPCIONAL) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Executado quando a condição do SE é falsa.

  REGRA "Irrigacao com Fallback" {
      SE umidade_solo < 30
      ENTAO irrigar("Setor A"; 15);
      SENAO disparar_alerta("Solo com umidade adequada");
  }

━━━ MÚLTIPLAS REGRAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Escreva quantas regras quiser no mesmo arquivo.
  Cada regra deve ter um nome único.

  REGRA "Regra 1" {
      SE temperatura_ar > 35
      ENTAO disparar_alerta("Calor extremo");
  }

  REGRA "Regra 2" {
      SE umidade_solo < 20 E luminosidade > 800
      ENTAO irrigar("Setor B"; 25);
  }

━━━ VALIDAÇÕES AUTOMÁTICAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  O compilador verifica automaticamente:
  • Variáveis inexistentes (erro semântico)
  • Duração de irrigação inválida (≤ 0)
  • Nomes de regras duplicados
  • Erros de sintaxe (tokens inesperados)
  • Erros léxicos (caracteres inválidos)
"""

# ------------------------------------------------------------------------------
# Paleta de cores — tema dark inspirado no One Dark (Atom/VS Code)
# ------------------------------------------------------------------------------
# Centralizar todas as cores aqui permite trocar o tema alterando apenas este dict.
CORES: dict[str, str] = {
    # Fundos (do mais escuro ao mais claro)
    "bg":        "#1E2127",   # Fundo principal da janela
    "bg2":       "#282C34",   # Fundo de painéis secundários (toolbar, header de aba)
    "bg3":       "#2C313A",   # Fundo de rótulos de cabeçalho dentro dos painéis

    # Bordas e divisores
    "border":    "#3E4451",   # Cor de borda entre painéis e divisores visuais

    # Verde — sucesso, palavras-chave de ação, strings no highlight
    "verde":      "#98C379",
    "verde_dark": "#3A5129",  # Fundo do botão Compilar (mais escuro que o verde)

    # Amarelo — strings literais no highlight
    "amarelo":   "#E5C07B",

    # Azul — funções e variáveis de sensor no highlight
    "azul":      "#61AFEF",

    # Roxo — palavras reservadas (REGRA, SE, ENTAO, ...) no highlight
    "roxo":      "#C678DD",

    # Vermelho — operadores relacionais e mensagens de erro
    "vermelho":  "#E06C75",

    # Tons neutros — texto, ícones e elementos secundários
    "cinza":     "#ABB2BF",   # Texto secundário e rótulos de painel
    "branco":    "#DCDFE4",   # Texto principal nos widgets de código

    # Cursor de inserção no editor de código
    "cursor":    "#528BFF",
}


# ==============================================================================
# CLASSE PRINCIPAL — AgroLangIDE
# ==============================================================================

class AgroLangIDE(tk.Tk):
    """
    Janela principal do AgroLang IDE.

    Herda de tk.Tk (janela raiz do Tkinter). Organiza a interface em quatro
    abas dentro de um ttk.Notebook:
        0 — Menu       : cartões de navegação para as demais abas
        1 — Exemplos   : listbox com 5 exemplos + painel de preview
        2 — Documentação: referência da linguagem em ScrolledText
        3 — Editor     : editor de código com highlight + painel de resultado

    Atributos públicos relevantes:
        nb          : ttk.Notebook principal
        txt_editor  : ScrolledText do editor de código (aba Editor)
        txt_saida   : ScrolledText do painel de resultado (aba Editor)
        lb_exemplos : tk.Listbox com os títulos dos exemplos (aba Exemplos)
        ex_code     : ScrolledText de preview do exemplo selecionado
        lbl_status  : tk.Label com o status da última compilação
    """

    def __init__(self):
        """
        Inicializa a janela principal e constrói toda a interface.

        Configura: título, tamanho inicial (960×680), tamanho mínimo (800×560),
        cor de fundo e chama _build_ui para montar todos os widgets.
        """
        super().__init__()
        self.title("AgroLang IDE")
        self.geometry("960x680")
        self.minsize(800, 560)
        self.configure(bg=CORES["bg"])
        self._build_ui()

    # ── Layout principal ──────────────────────────────────────────────────────

    def _build_ui(self):
        """
        Monta o layout principal da janela: barra de título + Notebook de 4 abas.

        Sequência de construção:
            1. Frame de cabeçalho fixo (altura 54px) com logo e subtítulo.
            2. Configuração do estilo visual do ttk.Notebook via ttk.Style.
            3. Criação do Notebook e seus quatro frames-filhos.
            4. Registro das abas com texto e emoji.
            5. Chamada dos quatro métodos _build_* para popular cada aba.
        """
        # ── Barra de título ───────────────────────────────────────────────────
        # Frame com altura fixa (pack_propagate=False evita que widgets internos
        # alterem a altura definida)
        header = tk.Frame(self, bg=CORES["bg2"], height=54)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="🌱  AgroLang IDE",
            font=("Courier", 16, "bold"),
            bg=CORES["bg2"], fg=CORES["verde"]
        ).pack(side="left", padx=20, pady=12)

        tk.Label(
            header, text="DSL para Monitoramento Agrícola Inteligente",
            font=("Courier", 10),
            bg=CORES["bg2"], fg=CORES["cinza"]
        ).pack(side="left", pady=12)

        # ── Estilo visual do Notebook ──────────────────────────────────────────
        # O tema "default" é necessário para que style.configure() funcione
        # corretamente no Windows, Linux e macOS.
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook",       background=CORES["bg"],  borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=CORES["bg3"],
                        foreground=CORES["cinza"],
                        font=("Courier", 11, "bold"),
                        padding=[18, 8])
        # Aba selecionada: fundo mais claro e texto verde
        style.map("TNotebook.Tab",
                  background=[("selected", CORES["bg2"])],
                  foreground=[("selected", CORES["verde"])])

        # ── Notebook principal ─────────────────────────────────────────────────
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        # Frames-filhos: um por aba (preenchidos pelos métodos _build_*)
        self.tab_menu     = tk.Frame(nb, bg=CORES["bg"])
        self.tab_exemplos = tk.Frame(nb, bg=CORES["bg"])
        self.tab_docs     = tk.Frame(nb, bg=CORES["bg"])
        self.tab_editor   = tk.Frame(nb, bg=CORES["bg"])

        nb.add(self.tab_menu,     text="  🏠  Menu  ")
        nb.add(self.tab_exemplos, text="  🌿  Exemplos  ")
        nb.add(self.tab_docs,     text="  📖  Documentação  ")
        nb.add(self.tab_editor,   text="  ⌨️   Editor  ")

        self.nb = nb   # Guardado para navegação programática entre abas

        # Constrói o conteúdo de cada aba
        self._build_menu()
        self._build_exemplos()
        self._build_docs()
        self._build_editor()

    # ── Aba Menu ──────────────────────────────────────────────────────────────

    def _build_menu(self):
        """
        Constrói a aba Menu com título, subtítulo e três cartões de navegação.

        Cada cartão é um tk.Frame com efeito de hover (fundo muda ao passar o
        mouse) e um botão que chama nb.select(índice) para navegar à aba alvo.

        Cartões:
            🌿 Exemplos   → aba índice 1
            📖 Documentação → aba índice 2
            ⌨️  Editor      → aba índice 3
        """
        f = self.tab_menu

        # Espaçador superior
        tk.Frame(f, bg=CORES["bg"], height=40).pack()

        # Título e subtítulo centralizados
        tk.Label(f, text="🌱 AgroLang IDE",
                 font=("Courier", 26, "bold"),
                 bg=CORES["bg"], fg=CORES["verde"]).pack()
        tk.Label(f, text="Compilador de DSL para Monitoramento Agrícola Inteligente",
                 font=("Courier", 12),
                 bg=CORES["bg"], fg=CORES["cinza"]).pack(pady=4)

        # Espaçador intermediário
        tk.Frame(f, bg=CORES["bg"], height=40).pack()

        # Container dos cartões (lado a lado)
        cards_frame = tk.Frame(f, bg=CORES["bg"])
        cards_frame.pack()

        # Definição dos cartões: (emoji, label, descrição, índice da aba alvo)
        opcoes = [
            ("🌿", "Exemplos",      "Explore regras prontas\npara cenários do campo", 1),
            ("📖", "Documentação",  "Referência completa\nda linguagem AgroLang",     2),
            ("⌨️",  "Editor",        "Escreva e compile\nsuas próprias regras",        3),
        ]

        for emoji, label, descricao, aba_idx in opcoes:
            # Cada cartão é um frame com dimensões fixas
            card = tk.Frame(cards_frame, bg=CORES["bg2"], width=220, height=170)
            card.pack(side="left", padx=16)
            card.pack_propagate(False)   # Mantém o tamanho fixo

            tk.Label(card, text=emoji,  font=("Courier", 30),
                     bg=CORES["bg2"], fg=CORES["verde"]).pack(pady=(28, 6))
            tk.Label(card, text=label,  font=("Courier", 14, "bold"),
                     bg=CORES["bg2"], fg=CORES["branco"]).pack()
            tk.Label(card, text=descricao, font=("Courier", 10),
                     bg=CORES["bg2"], fg=CORES["cinza"], justify="center").pack(pady=6)

            # Botão de navegação
            tk.Button(
                card, text="Abrir →",
                font=("Courier", 10, "bold"),
                bg=CORES["verde_dark"], fg=CORES["verde"],
                relief="flat", bd=0, cursor="hand2",
                command=lambda idx=aba_idx: self.nb.select(idx)
            ).pack(pady=4)

            # Efeito hover: altera o fundo do cartão ao passar o mouse
            card.bind("<Enter>", lambda e, c=card: c.configure(bg=CORES["bg3"]))
            card.bind("<Leave>", lambda e, c=card: c.configure(bg=CORES["bg2"]))

    # ── Aba Exemplos ──────────────────────────────────────────────────────────

    def _build_exemplos(self):
        """
        Constrói a aba Exemplos com layout dividido em PanedWindow horizontal.

        Painel esquerdo (largura mínima 200px):
            - tk.Listbox com os títulos de EXEMPLOS
            - Evento <<ListboxSelect>> → _mostrar_exemplo

        Painel direito (largura mínima 400px):
            - Labels de título e descrição do exemplo selecionado
            - Botões "Abrir no Editor" e "Compilar agora"
            - ScrolledText somente leitura com preview do código + highlight
        """
        f = self.tab_exemplos

        # Cabeçalho da aba
        tk.Label(f, text="Exemplos de Regras AgroLang",
                 font=("Courier", 13, "bold"),
                 bg=CORES["bg"], fg=CORES["verde"]).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(f, text="Clique em um exemplo para visualizar e carregar no editor",
                 font=("Courier", 10),
                 bg=CORES["bg"], fg=CORES["cinza"]).pack(anchor="w", padx=20)

        # PanedWindow: divisória arrastável entre lista e preview
        paned = tk.PanedWindow(f, orient="horizontal",
                               bg=CORES["border"], sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=12, pady=12)

        # ── Painel esquerdo: lista de exemplos ────────────────────────────────
        list_frame = tk.Frame(paned, bg=CORES["bg2"], width=260)
        paned.add(list_frame, minsize=200)

        self.lb_exemplos = tk.Listbox(
            list_frame,
            font=("Courier", 11),
            bg=CORES["bg2"], fg=CORES["branco"],
            selectbackground=CORES["verde_dark"],
            selectforeground=CORES["verde"],
            relief="flat", bd=0,
            activestyle="none",   # Remove o sublinhado do item ativo
            cursor="hand2"
        )
        for ex in EXEMPLOS:
            self.lb_exemplos.insert("end", f"  {ex['titulo']}")
        self.lb_exemplos.pack(fill="both", expand=True)
        # Vincula seleção ao método que atualiza o painel direito
        self.lb_exemplos.bind("<<ListboxSelect>>", self._mostrar_exemplo)

        # ── Painel direito: preview e ações ───────────────────────────────────
        right = tk.Frame(paned, bg=CORES["bg"])
        paned.add(right, minsize=400)

        # Título e descrição (atualizados por _mostrar_exemplo)
        self.ex_titulo = tk.Label(
            right, text="← Selecione um exemplo",
            font=("Courier", 13, "bold"),
            bg=CORES["bg"], fg=CORES["amarelo"]
        )
        self.ex_titulo.pack(anchor="w", padx=16, pady=(12, 2))

        self.ex_desc = tk.Label(
            right, text="",
            font=("Courier", 10),
            bg=CORES["bg"], fg=CORES["cinza"],
            wraplength=480, justify="left"
        )
        self.ex_desc.pack(anchor="w", padx=16)

        # Botões de ação sobre o exemplo selecionado
        btn_frame = tk.Frame(right, bg=CORES["bg"])
        btn_frame.pack(anchor="w", padx=16, pady=8)

        tk.Button(
            btn_frame, text="⌨️  Abrir no Editor",
            font=("Courier", 10, "bold"),
            bg=CORES["verde_dark"], fg=CORES["verde"],
            relief="flat", bd=0, cursor="hand2", padx=12, pady=5,
            command=self._carregar_no_editor
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="▶  Compilar agora",
            font=("Courier", 10, "bold"),
            bg=CORES["bg3"], fg=CORES["azul"],
            relief="flat", bd=0, cursor="hand2", padx=12, pady=5,
            command=self._compilar_exemplo
        ).pack(side="left")

        # Preview do código com highlight (somente leitura)
        tk.Label(right, text="Código:",
                 font=("Courier", 10, "bold"),
                 bg=CORES["bg"], fg=CORES["cinza"]).pack(anchor="w", padx=16)

        self.ex_code = scrolledtext.ScrolledText(
            right,
            font=("Courier", 11),
            bg=CORES["bg2"], fg=CORES["branco"],
            insertbackground=CORES["cursor"],
            relief="flat", bd=0,
            state="disabled",   # Somente leitura; habilitado temporariamente para inserção
            height=10
        )
        self.ex_code.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        # Registra as tags de cor para o highlight neste widget
        self._estilizar_texto(self.ex_code)

    def _mostrar_exemplo(self, event=None):
        """
        Atualiza o painel direito ao selecionar um exemplo na Listbox.

        Obtém o índice selecionado via curselection(), recupera o exemplo
        correspondente da lista EXEMPLOS e:
            1. Atualiza os labels de título e descrição.
            2. Habilita temporariamente o ScrolledText para inserção.
            3. Limpa o conteúdo anterior e insere o código do exemplo.
            4. Aplica o syntax highlighting.
            5. Desabilita o ScrolledText (somente leitura).

        Args:
            event: Evento Tkinter <<ListboxSelect>> (pode ser None se chamado
                   programaticamente).
        """
        sel = self.lb_exemplos.curselection()
        if not sel:
            return   # Nenhum item selecionado (pode ocorrer durante inicialização)

        ex = EXEMPLOS[sel[0]]
        self.ex_titulo.config(text=ex["titulo"])
        self.ex_desc.config(text=ex["descricao"])

        self.ex_code.config(state="normal")
        self.ex_code.delete("1.0", "end")
        self.ex_code.insert("end", ex["codigo"])
        self._aplicar_highlight(self.ex_code)
        self.ex_code.config(state="disabled")

    def _carregar_no_editor(self):
        """
        Copia o código do exemplo selecionado para o editor e navega para a aba Editor.

        Verifica se há um item selecionado na Listbox; exibe messagebox de aviso
        caso contrário. Se houver seleção, limpa o editor, insere o código,
        aplica o highlight e seleciona a aba Editor (índice 3).
        """
        sel = self.lb_exemplos.curselection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione um exemplo primeiro.")
            return

        codigo = EXEMPLOS[sel[0]]["codigo"]
        self.txt_editor.delete("1.0", "end")
        self.txt_editor.insert("end", codigo)
        self._aplicar_highlight(self.txt_editor)
        self.nb.select(3)   # Navega para a aba Editor

    def _compilar_exemplo(self):
        """
        Carrega o exemplo selecionado no editor e dispara a compilação imediatamente.

        Equivale a chamar _carregar_no_editor() seguido de _compilar(). O usuário
        vê o código carregado no editor e o resultado já exibido no painel de saída.
        """
        sel = self.lb_exemplos.curselection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione um exemplo primeiro.")
            return

        codigo = EXEMPLOS[sel[0]]["codigo"]
        self.txt_editor.delete("1.0", "end")
        self.txt_editor.insert("end", codigo)
        self._aplicar_highlight(self.txt_editor)
        self.nb.select(3)
        self._compilar()   # Compila imediatamente após carregar

    # ── Aba Documentação ──────────────────────────────────────────────────────

    def _build_docs(self):
        """
        Constrói a aba Documentação com o conteúdo da constante DOCUMENTACAO.

        Cria um ScrolledText configurado como somente leitura e insere o texto
        pré-formatado. As tags de cor (verde, amarelo, azul) são registradas
        para uso futuro de highlight na documentação.
        """
        f = self.tab_docs

        tk.Label(f, text="Documentação da Linguagem AgroLang",
                 font=("Courier", 13, "bold"),
                 bg=CORES["bg"], fg=CORES["verde"]).pack(anchor="w", padx=20, pady=(16, 8))

        txt = scrolledtext.ScrolledText(
            f,
            font=("Courier", 11),
            bg=CORES["bg2"], fg=CORES["branco"],
            insertbackground=CORES["cursor"],
            relief="flat", bd=0,
            state="normal",
            wrap="word"
        )
        txt.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        txt.insert("end", DOCUMENTACAO)
        txt.config(state="disabled")   # Somente leitura após inserção

        # Registra tags de cor (preparação para highlight da documentação)
        txt.config(state="normal")
        for tag, cor in [
            ("verde",   CORES["verde"]),
            ("amarelo", CORES["amarelo"]),
            ("azul",    CORES["azul"]),
        ]:
            txt.tag_configure(tag, foreground=cor)
        txt.config(state="disabled")

    # ── Aba Editor ────────────────────────────────────────────────────────────

    def _build_editor(self):
        """
        Constrói a aba Editor com toolbar, editor de código e painel de resultado.

        Layout:
            ┌──────────────────────────────────────────────────┐
            │  [▶ Compilar]  [🗑 Limpar]  [status]  (toolbar)  │
            ├───────────────────────┬──────────────────────────┤
            │   Código AgroLang     │   Resultado da Compilação │
            │   (txt_editor)        │   (txt_saida)             │
            │   • editável          │   • somente leitura       │
            │   • undo=True         │   • scroll automático     │
            │   • Ctrl+Enter → compila                         │
            │   • KeyRelease → highlight                       │
            └───────────────────────┴──────────────────────────┘

        Após construir os widgets, insere um código de dica inicial no editor
        e aplica o highlight inicial.
        """
        f = self.tab_editor

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = tk.Frame(f, bg=CORES["bg2"], height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Button(
            toolbar, text="▶  Compilar",
            font=("Courier", 11, "bold"),
            bg=CORES["verde_dark"], fg=CORES["verde"],
            relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
            command=self._compilar
        ).pack(side="left", padx=(12, 6), pady=6)

        tk.Button(
            toolbar, text="🗑  Limpar",
            font=("Courier", 10),
            bg=CORES["bg3"], fg=CORES["cinza"],
            relief="flat", bd=0, cursor="hand2", padx=10, pady=6,
            command=self._limpar_editor
        ).pack(side="left", padx=4, pady=6)

        # Label de status: atualizado após cada compilação
        self.lbl_status = tk.Label(
            toolbar, text="",
            font=("Courier", 10, "bold"),
            bg=CORES["bg2"], fg=CORES["verde"]
        )
        self.lbl_status.pack(side="left", padx=12)

        # ── PanedWindow: editor | saída ───────────────────────────────────────
        paned = tk.PanedWindow(f, orient="horizontal",
                               bg=CORES["border"], sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=0, pady=0)

        # Painel esquerdo — editor de código
        left = tk.Frame(paned, bg=CORES["bg"])
        paned.add(left, minsize=300)

        tk.Label(left, text="  Código AgroLang",
                 font=("Courier", 10, "bold"),
                 bg=CORES["bg3"], fg=CORES["cinza"], anchor="w").pack(fill="x")

        self.txt_editor = scrolledtext.ScrolledText(
            left,
            font=("Courier", 12),
            bg=CORES["bg2"], fg=CORES["branco"],
            insertbackground=CORES["cursor"],
            relief="flat", bd=0,
            undo=True,      # Habilita Ctrl+Z / Ctrl+Y para desfazer/refazer
            wrap="none"     # Sem quebra automática de linha
        )
        self.txt_editor.pack(fill="both", expand=True)

        # KeyRelease → reaplica highlight após cada tecla digitada
        self.txt_editor.bind("<KeyRelease>",
                             lambda e: self._aplicar_highlight(self.txt_editor))
        # Ctrl+Enter → atalho para compilar sem usar o mouse
        self.txt_editor.bind("<Control-Return>", lambda e: self._compilar())

        # Painel direito — resultado da compilação (somente leitura)
        right = tk.Frame(paned, bg=CORES["bg"])
        paned.add(right, minsize=300)

        tk.Label(right, text="  Resultado da Compilação",
                 font=("Courier", 10, "bold"),
                 bg=CORES["bg3"], fg=CORES["cinza"], anchor="w").pack(fill="x")

        self.txt_saida = scrolledtext.ScrolledText(
            right,
            font=("Courier", 11),
            bg=CORES["bg2"], fg=CORES["branco"],
            insertbackground=CORES["cursor"],
            relief="flat", bd=0,
            state="disabled",   # Somente leitura; habilitado temporariamente por _compilar
            wrap="word"
        )
        self.txt_saida.pack(fill="both", expand=True)

        # Registra as tags de cor em ambos os widgets
        self._estilizar_texto(self.txt_editor)
        self._estilizar_texto(self.txt_saida)

        # Insere código de dica inicial no editor com highlight aplicado
        dica = (
            '# Bem-vindo ao AgroLang IDE!\n'
            '# Escreva suas regras abaixo ou carregue um exemplo.\n'
            '# Atalho: Ctrl+Enter para compilar.\n\n'
            'REGRA "Minha Primeira Regra" {\n'
            '    SE umidade_solo < 30\n'
            '    ENTAO irrigar("Setor A"; 20);\n'
            '}'
        )
        self.txt_editor.insert("end", dica)
        self._aplicar_highlight(self.txt_editor)

    # ── Compilação ────────────────────────────────────────────────────────────

    def _compilar(self):
        """
        Lê o conteúdo do editor, compila e exibe o resultado no painel de saída.

        Fluxo:
            1. Lê e strip() o conteúdo do txt_editor.
            2. Remove linhas de comentário (iniciadas com #).
            3. Verifica se há código não-vazio após a remoção.
            4. Chama compilar() do Módulo 4.
            5a. Sucesso: exibe cabeçalho, itera sobre as regras chamando
                _imprimir_condicao e _imprimir_acao, exibe o JSON formatado
                e atualiza lbl_status com contagem de regras.
            5b. Erro: exibe a mensagem de exceção com cor vermelha e atualiza
                lbl_status com indicador de falha.
            6. Desabilita txt_saida ao final (somente leitura).
        """
        codigo = self.txt_editor.get("1.0", "end").strip()

        # Habilita o painel de saída para escrita e limpa conteúdo anterior
        self.txt_saida.config(state="normal")
        self.txt_saida.delete("1.0", "end")

        # Remove linhas de comentário antes de enviar ao compilador
        if not codigo or codigo.startswith('#'):
            linhas = [l for l in codigo.split('\n') if not l.strip().startswith('#')]
            codigo = '\n'.join(linhas).strip()

        # Guarda se há código real a compilar
        if not codigo:
            self._set_saida("⚠  Nenhum código para compilar.", CORES["amarelo"])
            self.lbl_status.config(text="⚠ Vazio", fg=CORES["amarelo"])
            return

        try:
            # Chama o compilador completo (Módulo 4)
            resultado = compilar(codigo)
            n = len(resultado["regras"])

            # Cabeçalho de sucesso
            cabecalho = f"✓  Compilado com sucesso — {n} regra(s) encontrada(s)\n"
            cabecalho += "─" * 56 + "\n\n"
            self.txt_saida.insert("end", cabecalho, "ok")

            # Exibe cada regra com suas condições e ações formatadas
            for regra in resultado["regras"]:
                self.txt_saida.insert("end", "  REGRA: ", "label")
                self.txt_saida.insert("end", f'"{regra["nome"]}"\n', "str")
                self._imprimir_condicao(regra["condicao"], indent=4)
                self.txt_saida.insert("end", "    ENTAO: ", "label")
                self._imprimir_acao(regra["entao"])
                if regra["senao"]:
                    self.txt_saida.insert("end", "    SENAO: ", "label")
                    self._imprimir_acao(regra["senao"])
                self.txt_saida.insert("end", "\n")

            # JSON formatado para inspeção/cópia
            self.txt_saida.insert("end", "─" * 56 + "\n\n", "borda")
            self.txt_saida.insert("end", "JSON gerado:\n\n", "label")
            self.txt_saida.insert(
                "end",
                json.dumps(resultado, indent=2, ensure_ascii=False),
                "json"
            )

            self.lbl_status.config(
                text=f"✓  {n} regra(s) compilada(s)", fg=CORES["verde"]
            )

        except (SyntaxError, ValueError) as e:
            # Exibe mensagem de erro com cor vermelha
            self._set_saida(f"✗  Erro de compilação:\n\n{e}", CORES["vermelho"])
            self.lbl_status.config(text="✗  Erro", fg=CORES["vermelho"])

        finally:
            # Sempre desabilita o painel de saída ao terminar
            self.txt_saida.config(state="disabled")

    def _imprimir_condicao(self, cond: dict, indent: int = 4):
        """
        Renderiza uma condição do JSON no painel de saída com tags de cor.

        Método recursivo: para condições do tipo 'logica', chama a si mesmo
        nos filhos, intercalando o operador entre eles. Para condições do tipo
        'comparacao', formata a linha com variável, operador, valor e módulo.

        Args:
            cond:   Dicionário de condição gerado pelo compilador.
            indent: Número de espaços de indentação (aumenta na recursão).
        """
        sp = " " * indent

        if cond["tipo"] == "comparacao":
            # Linha de comparação simples: "    SE  variavel op valor  [modulo]"
            self.txt_saida.insert("end", f"{sp}SE  ", "label")
            self.txt_saida.insert("end", cond["variavel"],         "var")
            self.txt_saida.insert("end", f" {cond['operador']} ",  "op")
            self.txt_saida.insert("end", f"{cond['valor']}",       "num")
            self.txt_saida.insert("end", f"  [{cond['modulo']}]\n","modulo")
        else:
            # Condição lógica: exibe esquerda, operador e direita em linhas
            self._imprimir_condicao(cond["esquerda"], indent)
            self.txt_saida.insert("end", f"{sp}  {cond['operador']}\n", "op")
            self._imprimir_condicao(cond["direita"],  indent)

    def _imprimir_acao(self, acao: dict):
        """
        Renderiza uma ação do JSON no painel de saída com tags de cor.

        Args:
            acao: Dicionário de ação gerado pelo compilador.
                  Tipos esperados: 'disparar_alerta' ou 'irrigar'.
        """
        if acao["tipo"] == "disparar_alerta":
            self.txt_saida.insert("end", "disparar_alerta(", "fn")
            self.txt_saida.insert("end", f'"{acao["mensagem"]}"', "str")
            self.txt_saida.insert("end", ")\n", "fn")
        else:
            # acao_irrigar: exibe zona e duração
            self.txt_saida.insert("end", "irrigar(", "fn")
            self.txt_saida.insert("end", f'"{acao["zona"]}"', "str")
            self.txt_saida.insert("end", f'; {acao["duracao_minutos"]} min)\n', "num")

    def _set_saida(self, texto: str, cor: str):
        """
        Exibe uma mensagem única e colorida no painel de saída.

        Utilitário usado para mensagens de aviso (código vazio) e de erro
        (erros de compilação). Habilita, limpa, insere com a tag 'msg'
        configurada com a cor informada e desabilita o widget.

        Args:
            texto: Mensagem a exibir.
            cor:   Código hexadecimal da cor do texto (ex: CORES["vermelho"]).
        """
        self.txt_saida.config(state="normal")
        self.txt_saida.delete("1.0", "end")
        self.txt_saida.insert("end", texto, "msg")
        self.txt_saida.tag_configure("msg", foreground=cor)
        self.txt_saida.config(state="disabled")

    def _limpar_editor(self):
        """
        Apaga todo o conteúdo do editor e do painel de saída, limpa o status.

        Chamado pelo botão "🗑 Limpar" da toolbar.
        """
        self.txt_editor.delete("1.0", "end")
        self.txt_saida.config(state="normal")
        self.txt_saida.delete("1.0", "end")
        self.txt_saida.config(state="disabled")
        self.lbl_status.config(text="")

    # ── Syntax Highlighting ───────────────────────────────────────────────────

    def _estilizar_texto(self, widget: scrolledtext.ScrolledText):
        """
        Configura as tags de cor e fonte usadas pelo syntax highlighting.

        Deve ser chamada uma vez por widget ScrolledText antes de qualquer
        uso de _aplicar_highlight ou inserção com tags no painel de saída.
        As tags aqui definidas são usadas tanto para colorir o código no editor
        quanto para formatar o resultado no painel de saída.

        Tags configuradas:
            keyword  → palavras reservadas (roxo, negrito)
            fn       → funções de ação (azul)
            str      → strings literais (verde)
            num      → números (amarelo)
            var      → variáveis de sensor (azul)
            op       → operadores relacionais (vermelho)
            comment  → comentários # (cinza, itálico)
            ok       → cabeçalho de sucesso (verde, negrito)
            label    → rótulos no painel de saída (cinza)
            modulo   → nome do módulo entre colchetes (cinza borda)
            borda    → linha divisória no painel de saída (cinza borda)
            json     → JSON gerado (cinza)

        Args:
            widget: ScrolledText a ser configurado.
        """
        widget.tag_configure("keyword", foreground=CORES["roxo"],    font=("Courier", 12, "bold"))
        widget.tag_configure("fn",      foreground=CORES["azul"],    font=("Courier", 12))
        widget.tag_configure("str",     foreground=CORES["verde"])
        widget.tag_configure("num",     foreground=CORES["amarelo"])
        widget.tag_configure("var",     foreground=CORES["azul"])
        widget.tag_configure("op",      foreground=CORES["vermelho"])
        widget.tag_configure("comment", foreground=CORES["border"],  font=("Courier", 12, "italic"))
        widget.tag_configure("ok",      foreground=CORES["verde"],   font=("Courier", 11, "bold"))
        widget.tag_configure("label",   foreground=CORES["cinza"])
        widget.tag_configure("modulo",  foreground=CORES["border"])
        widget.tag_configure("borda",   foreground=CORES["border"])
        widget.tag_configure("json",    foreground=CORES["cinza"])

    def _aplicar_highlight(self, widget: scrolledtext.ScrolledText):
        """
        Aplica syntax highlighting ao conteúdo de um ScrolledText.

        Algoritmo:
            1. Remove todas as tags de highlight existentes do widget inteiro
               (evita duplicação ao redigitar).
            2. Obtém o texto atual via widget.get("1.0", "end").
            3. Para cada padrão regex, usa re.finditer para localizar todos os
               matches e adiciona a tag correspondente usando posições no formato
               "1.0 + N chars" exigido pelo Tkinter.

        A ordem dos padrões é importante para evitar conflitos:
            1. comments  → comentários têm prioridade máxima
            2. keywords  → palavras reservadas
            3. fns       → funções de ação (disparar_alerta, irrigar)
            4. strings   → literais de texto
            5. variaveis → identificadores de sensor
            6. nums      → literais numéricos
            7. ops       → operadores relacionais

        Nota: este highlight é aproximado (regex sobre texto plano, não sobre
        tokens). Funciona bem para os casos de uso da AgroLang, mas pode
        colorir erroneamente strings que contenham palavras reservadas.

        Args:
            widget: ScrolledText sobre o qual aplicar o highlight.
        """
        # Passo 1: limpa todas as tags de highlight do widget
        for tag in ["keyword", "fn", "str", "num", "var", "op", "comment"]:
            widget.tag_remove(tag, "1.0", "end")

        # Passo 2: obtém o texto completo atual
        texto = widget.get("1.0", "end")

        # Padrões regex e suas tags correspondentes
        variaveis_pattern = '|'.join(VARIAVEIS_NUMERICAS)   # Gera regex ORed
        patterns = [
            (r'#[^\n]*',                 "comment"),   # Comentários de linha
            (r'\b(REGRA|SE|ENTAO|SENAO|E|OU)\b', "keyword"),   # Palavras reservadas
            (r'\b(disparar_alerta|irrigar)\b',   "fn"),         # Funções de ação
            (r'"[^"]*"',                 "str"),       # Strings entre aspas duplas
            (variaveis_pattern,          "var"),       # Variáveis de sensor
            (r'\b\d+(\.\d+)?\b',         "num"),       # Números inteiros e decimais
            (r'(>=|<=|==|!=|>|<)',       "op"),        # Operadores relacionais
        ]

        # Passo 3: aplica cada padrão
        for pattern, tag in patterns:
            for m in re.finditer(pattern, texto):
                # Converte posição de char para o formato "linha.coluna + N chars"
                start = f"1.0 + {m.start()} chars"
                end   = f"1.0 + {m.end()} chars"
                widget.tag_add(tag, start, end)


# ==============================================================================
# PONTO DE ENTRADA
# ==============================================================================

if __name__ == "__main__":
    """
    Executa o AgroLang IDE quando o script é chamado diretamente.

    Cria a instância de AgroLangIDE (que também é a janela tk.Tk raiz)
    e inicia o loop principal de eventos do Tkinter com mainloop().
    O loop bloqueia até que o usuário feche a janela.
    """
    app = AgroLangIDE()
    app.mainloop()
