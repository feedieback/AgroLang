<div align="center">

# 🌱 AgroLang IDE

**Compilador de Linguagem de Domínio Específico para Monitoramento Agrícola Inteligente**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PLY](https://img.shields.io/badge/PLY-3.11-green?style=flat-square)](https://github.com/dabeaz/ply)
[![Tkinter](https://img.shields.io/badge/GUI-Tkinter-orange?style=flat-square)](https://docs.python.org/3/library/tkinter.html)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Estável-brightgreen?style=flat-square)]()

*Escreva regras agrícolas em português. Compile para JSON. Automatize o campo.*

</div>

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Demonstração](#-demonstração)
- [Funcionalidades](#-funcionalidades)
- [Instalação](#-instalação)
- [Como Usar](#-como-usar)
- [A Linguagem AgroLang](#-a-linguagem-agrolang)
- [Arquitetura](#-arquitetura)
- [Exemplos](#-exemplos)
- [Integração com Hardware](#-integração-com-hardware)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Referências](#-referências)
- [Autor](#-autor)

---

## 🌾 Sobre o Projeto

A **AgroLang** é uma **Linguagem de Domínio Específico (DSL)** projetada para abstrair a complexidade de sistemas de automação agrícola. Em vez de programar diretamente o firmware de microcontroladores ou escrever scripts de backend, o produtor rural define comportamentos de manejo através de **regras declarativas em português**.

O compilador traduz essas regras em objetos **JSON estruturados**, que atuam como linguagem intermediária universal — prontos para serem despachados via **MQTT** para microcontroladores **ESP32**, servidores **Apache** ou dashboards web.

Este projeto é o componente de software de alto nível do [Sistema Inteligente de Monitoramento Agrícola](https://github.com/feedieback/TCC), integrando-se nativamente com:

- **Módulo 1** — Sensores de solo, ar e ambiente via ESP32
- **Módulo 2** — Detecção de pragas por visão computacional (YOLOv8)

---

## 🖥️ Demonstração

```
┌─────────────────────────────────────────────────────────────┐
│  🌱  AgroLang IDE     DSL para Monitoramento Agrícola        │
├──────────────┬──────────────┬───────────────┬───────────────┤
│  🏠  Menu    │  🌿 Exemplos │  📖  Docs     │  ⌨️  Editor   │
├──────────────┴──────────────┴───────────────┴───────────────┤
│  Código AgroLang              │  Resultado da Compilação     │
│                               │                              │
│  REGRA "Irrigação Setor A" {  │  ✓ Compilado — 1 regra(s)   │
│      SE umidade_solo < 30     │  ──────────────────────────  │
│      ENTAO irrigar(           │  REGRA: "Irrigação Setor A"  │
│          "Setor A"; 20);      │    SE  umidade_solo < 30     │
│  }                            │        [Módulo 1 - Solo]     │
│                               │    ENTAO: irrigar(           │
│  [▶ Compilar]  [🗑 Limpar]   │        "Setor A"; 20 min)    │
└───────────────────────────────┴──────────────────────────────┘
```

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 🔤 **Análise Léxica** | Tokenização via expressões regulares com PLY |
| 🌳 **Análise Sintática** | Parser LALR(1) com construção de AST |
| ✅ **Análise Semântica** | Validação de variáveis, nomes duplicados e parâmetros |
| 📦 **Geração de Código** | Serialização AST → JSON com metadados de módulo |
| 🎨 **Syntax Highlighting** | Realce de sintaxe em tempo real no editor |
| 📚 **Exemplos Integrados** | 5 cenários de uso prontos para carregar e compilar |
| 📖 **Documentação Built-in** | Referência completa da linguagem dentro da IDE |
| ⌨️ **Atalhos de Teclado** | `Ctrl+Enter` para compilar |

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- tkinter (já incluído no Python padrão)

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/feedieback/TCC.git
cd TCC

# 2. Instale a única dependência externa
pip install ply

# 3. Execute a IDE
python N2.py
```

> **Nota:** O tkinter já vem instalado com o Python na maioria das distribuições. Se necessário: `sudo apt-get install python3-tk` (Linux/Debian).

---

## 🎮 Como Usar

### Via IDE Gráfica

1. Execute `python N2.py`
2. Na aba **Exemplos**, explore cenários prontos e clique em **"Compilar agora"** para ver o resultado
3. Na aba **Editor**, escreva suas próprias regras
4. Pressione **`Ctrl+Enter`** ou clique em **"▶ Compilar"**
5. O JSON gerado aparece no painel direito, pronto para uso

### Via Código Python

```python
from N2 import compilar

codigo = '''
REGRA "Irrigação Automática" {
    SE umidade_solo < 30 E temperatura_ar > 32
    ENTAO irrigar("Setor A"; 20);
    SENAO disparar_alerta("Solo com umidade adequada");
}
'''

resultado = compilar(codigo)
print(resultado)
# {'regras': [{'nome': 'Irrigação Automática', 'condicao': {...}, 'entao': {...}, 'senao': {...}}]}
```

---

## 📝 A Linguagem AgroLang

### Estrutura Básica

```
REGRA "Nome da Regra" {
    SE <condição>
    ENTAO <ação>;
    SENAO <ação>;    ← opcional
}
```

### Variáveis de Sensor

| Variável | Módulo | Descrição |
|---|---|---|
| `umidade_solo` | Módulo 1 — Solo | % de umidade do solo |
| `temperatura_solo` | Módulo 1 — Solo | Temperatura do solo (°C) |
| `ph_solo` | Módulo 1 — Solo | pH do solo |
| `nivel_agua` | Módulo 1 — Solo | Nível de água no reservatório |
| `umidade_ar` | Módulo 1 — Ar | % de umidade relativa do ar |
| `temperatura_ar` | Módulo 1 — Ar | Temperatura do ar (°C) |
| `luminosidade` | Módulo 1 — Ambiente | Nível de luminosidade (lux) |
| `contagem_pragas` | Módulo 2 — Visão Comp. | Nº de pragas detectadas (YOLOv8) |
| `indice_saude` | Módulo 2 — Visão Comp. | Índice de saúde foliar (0–100) |

### Operadores

```
Relacionais:   >   <   ==   >=   <=   !=
Lógicos:       E (AND)     OU (OR)
```

### Ações Disponíveis

```
disparar_alerta("mensagem");       → Notificação no dashboard via MQTT
irrigar("zona"; minutos);          → Aciona relé do ESP32 (minutos > 0)
```

### Validações Automáticas

O compilador detecta e reporta automaticamente:

- ❌ Variáveis de sensor inexistentes
- ❌ Duração de irrigação inválida (`≤ 0`)
- ❌ Nomes de regras duplicados no mesmo arquivo
- ❌ Erros de sintaxe (tokens inesperados)
- ❌ Erros léxicos (caracteres inválidos)

---

## 🏗️ Arquitetura

O compilador é dividido em cinco módulos sequenciais:

```
Código-fonte AgroLang
        │
        ▼
┌───────────────┐
│  Módulo 1     │  Análise Léxica
│  Lexer (PLY)  │  Tokenização via regex
└───────┬───────┘
        │  tokens
        ▼
┌───────────────┐
│  Módulo 2     │  Análise Sintática
│  Parser (PLY) │  Gramática LALR(1) → AST
└───────┬───────┘
        │  AST (NoAST)
        ▼
┌───────────────┐
│  Módulo 3     │  Análise Semântica
│  Semântico    │  Validação de invariantes
└───────┬───────┘
        │  AST validada
        ▼
┌───────────────┐
│  Módulo 4     │  Geração de Código
│  Gerador JSON │  AST → dicionário Python/JSON
└───────┬───────┘
        │  JSON
        ▼
┌───────────────┐
│  Módulo 5     │  Interface Gráfica
│  IDE tkinter  │  Editor + Highlighting + Saída
└───────────────┘
```

### Gramática BNF (resumo)

```bnf
<programa>  ::= <lista_regras>
<regra>     ::= REGRA <string> { SE <cond> ENTAO <acao> [SENAO <acao>] }
<cond>      ::= <cond> E <cond> | <cond> OU <cond> | <id> <op_rel> <num>
<op_rel>    ::= > | < | == | >= | <= | !=
<acao>      ::= disparar_alerta(<string>);
              | irrigar(<string>; <num>);
```

---

## 💡 Exemplos

### 1. Alerta de Praga
```
REGRA "Alerta de Praga" {
    SE contagem_pragas > 30 E umidade_ar > 75
    ENTAO disparar_alerta("ALTO RISCO: Mosca Branca detectada");
}
```

### 2. Irrigação com Fallback
```
REGRA "Controle de Irrigação" {
    SE umidade_solo < 30
    ENTAO irrigar("Setor B"; 15);
    SENAO disparar_alerta("Solo com umidade adequada");
}
```

### 3. Múltiplas Regras
```
REGRA "Irrigação Inteligente" {
    SE umidade_solo < 25 E temperatura_ar > 32
    ENTAO irrigar("Setor C"; 30);
    SENAO disparar_alerta("Irrigação não necessária");
}

REGRA "Praga Urgente" {
    SE contagem_pragas > 50
    ENTAO disparar_alerta("URGENTE: Aplicar defensivo agrícola");
}
```

### JSON gerado (exemplo)

```json
{
  "regras": [{
    "nome": "Controle de Irrigação",
    "condicao": {
      "tipo": "comparacao",
      "variavel": "umidade_solo",
      "modulo": "Módulo 1 - Solo",
      "operador": "<",
      "valor": 30
    },
    "entao": {
      "tipo": "irrigar",
      "zona": "Setor B",
      "duracao_minutos": 15
    },
    "senao": {
      "tipo": "disparar_alerta",
      "mensagem": "Solo com umidade adequada"
    }
  }]
}
```

---

## 🔌 Integração com Hardware

O JSON gerado pela AgroLang pode ser consumido por diferentes destinos:

```
JSON AgroLang
      │
      ├──► MQTT Broker ──► Dashboard Web (alertas em tempo real)
      │
      ├──► ESP32 + ArduinoJson ──► Relé de irrigação
      │                       └──► Notificações push
      │
      └──► Servidor Apache ──► API REST / banco de dados
```

**Publicação via MQTT (Python):**
```python
import paho.mqtt.client as mqtt
import json
from N2 import compilar

regras = compilar(codigo)
client = mqtt.Client()
client.connect("broker.hivemq.com", 1883)
client.publish("agrolang/regras", json.dumps(regras))
```

---

## 📁 Estrutura do Projeto

```
TCC/
├── N2.py                  # Compilador AgroLang + IDE (arquivo principal)
├── README.md              # Este arquivo
├── requirements.txt       # Dependências (ply)
├── parser.out             # Gerado automaticamente pelo PLY (debug)
└── parsetab.py            # Tabelas LALR geradas pelo PLY (cache)
```

**`requirements.txt`**
```
ply>=3.11
```

---

## 📚 Referências

- M. Mernik, J. Heering, A. M. Sloane, *"When and how to develop domain-specific languages"*, ACM Computing Surveys, vol. 37, n. 4, pp. 316–344, 2005.
- D. Beazley, [PLY (Python Lex-Yacc)](https://github.com/dabeaz/ply)
- W. Groeneveld et al., *"A domain-specific language framework for farm management information systems in precision agriculture"*, Precision Agriculture, vol. 22, 2021.
- J. Pérez et al., *"A Domain Specific Language Proposal for IoT Oriented to Smart Agro"*, IEEE Access, 2023.

---

## 👨‍💻 Autor

**Victor Augusto de Oliveira**
Engenharia da Computação — FHO Fundação Herminio Ometto, Araras, Brasil
📧 victoroliveira855@alunos.fho.edu.br
🔗 [github.com/feedieback/TCC](https://github.com/feedieback/TCC)

---

<div align="center">

*Feito com 🌱 para a agricultura familiar brasileira*

</div>
