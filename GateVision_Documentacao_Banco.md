# GateVision — Documentação Técnica do Banco de Dados
s
> Sistema de Controle de Acesso por Reconhecimento de Placas (ALPR)  
> **PostgreSQL 17 | Supabase | PL/pgSQL**

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Tabelas](#2-tabelas)
3. [Views](#3-views)
4. [Functions (PL/pgSQL)](#4-functions-plpgsql)
5. [Triggers](#5-triggers)
6. [Diagrama de Relacionamentos](#6-diagrama-de-relacionamentos)
7. [Tecnologias Utilizadas](#7-tecnologias-utilizadas)

---

## 1. Visão Geral

O banco de dados do GateVision foi projetado em **PostgreSQL 17**, hospedado no **Supabase**, para suportar um sistema completo de controle de acesso por reconhecimento automático de placas (ALPR) para condomínios e estabelecimentos similares.

| Componente | Quantidade | Descrição |
|---|---|---|
| Tabelas | 17 | Estrutura principal de dados do sistema |
| Views | 3 | Consultas pré-otimizadas para o frontend |
| Functions (PL/pgSQL) | 5 | Lógica de negócio centralizada no banco |
| Triggers | 7 | Automações disparadas por eventos |
| Perfis de acesso | 4 | Admin, Porteiro, Síndico, Gerente |

---

## 2. Tabelas

### 2.1 Tabelas de Domínio (Lookup)

Armazenam tipos e categorias utilizados pelas tabelas principais. São imutáveis no uso diário do sistema.

| Tabela | Colunas | Descrição |
|---|---|---|
| `tipos_veiculo` | id, descricao (UNIQUE) | Carro, Moto, Caminhão, etc. |
| `tipos_camera` | id, descricao (UNIQUE) | Tipo de câmera de acesso |
| `tipos_estabelecimento` | id, descricao (UNIQUE) | Condomínio, Hotel, Empresa, etc. |
| `tipos_vinculo` | id, descricao (UNIQUE) | Proprietário, Locatário, Funcionário, etc. |
| `perfis_acesso` | id, descricao (UNIQUE) | Admin, Porteiro, Síndico, Gerente |

---

### 2.2 estabelecimentos

Representa o condomínio ou empresa cadastrada no sistema. É a **entidade raiz** — quase tudo no banco está vinculado a um estabelecimento.

| Coluna | Tipo | Restrição | Descrição |
|---|---|---|---|
| id | integer | PK, auto-increment | Identificador único |
| nome | varchar(255) | NOT NULL | Nome do estabelecimento |
| cnpj | varchar(18) | UNIQUE | CNPJ (opcional) |
| tipo_estabelecimento_id | integer | FK → tipos_estabelecimento | Tipo do local |
| cep / logradouro / cidade / uf | varchar | Opcionais | Endereço completo |
| telefone / email | varchar | Opcionais | Contato |
| ativo | boolean | DEFAULT true | Soft delete |
| criado_em / atualizado_em | timestamp | DEFAULT now() | Auditoria automática |

---

### 2.3 blocos → unidades (Hierarquia do Condomínio)

Estrutura hierárquica que organiza as unidades habitacionais dentro do estabelecimento.

| Tabela | Coluna chave | Vincula a | Descrição |
|---|---|---|---|
| `blocos` | estabelecimento_id (FK) | estabelecimentos | Torres/blocos do condomínio |
| `blocos` | nome (UNIQUE por bloco) | — | Ex: Bloco A, Torre 1 |
| `unidades` | bloco_id (FK) | blocos | Apartamentos/salas |
| `unidades` | identificacao (UNIQUE) | — | Ex: 101, 202A |
| `unidades` | andar (integer) | — | Número do andar |

---

### 2.4 pessoas

Moradores, visitantes e funcionários. CPF é único quando informado.

| Coluna | Tipo | Restrição |
|---|---|---|
| id | integer | PK |
| nome | varchar(255) | NOT NULL |
| cpf | varchar(14) | UNIQUE (quando informado) |
| rg / telefone / email | varchar | Opcionais |
| observacao | text | Opcional |
| ativo | boolean | DEFAULT true — soft delete |

---

### 2.5 veiculos

Placas autorizadas, sempre vinculadas a uma pessoa. Possui validações no banco para garantir integridade.

| Coluna | Tipo | Restrição | Detalhe |
|---|---|---|---|
| id | integer | PK | — |
| pessoa_id | integer | FK → pessoas, NOT NULL | Proprietário obrigatório |
| placa | varchar(10) | UNIQUE + CHECK(length >= 7) | Ex: ABC1234 ou ABC1D23 |
| tipo_veiculo_id | integer | FK → tipos_veiculo, NOT NULL | — |
| marca / modelo / cor | varchar | Opcionais | — |
| ano_fabricacao | integer | CHECK >= 1900 | Valida ano mínimo |
| ativo | boolean | DEFAULT true | Soft delete |

---

### 2.6 vinculos

Relaciona pessoa com unidade com um tipo de vínculo. Suporta data de início e fim para controle histórico.

| Coluna | Tipo | Descrição |
|---|---|---|
| pessoa_id | FK → pessoas | Quem está vinculado |
| unidade_id | FK → unidades | Onde mora/trabalha |
| tipo_vinculo_id | FK → tipos_vinculo | Como está vinculado |
| data_inicio | date DEFAULT CURRENT_DATE | Início do vínculo |
| data_fim | date NULL | Fim do vínculo (NULL = ativo) |
| ativo | boolean DEFAULT true | Soft delete |

---

### 2.7 cameras

Câmeras cadastradas por estabelecimento. Cada leitura de placa é vinculada a uma câmera específica.

| Coluna | Tipo | Descrição |
|---|---|---|
| estabelecimento_id | FK → estabelecimentos | A qual condomínio pertence |
| tipo_camera_id | FK → tipos_camera | Tipo da câmera |
| nome | varchar(100) UNIQUE | Nome de identificação |
| ip_camera / porta | varchar / integer | Endereço de rede da câmera |
| resolucao | varchar(20) | Ex: 1920x1080 |
| ativo | boolean DEFAULT true | Soft delete |

---

### 2.8 acessos

Tabela de log principal. Registra **cada leitura de placa** feita pelo sistema, autorizada ou não. É a tabela de maior volume de dados.

| Coluna | Tipo | Restrição | Descrição |
|---|---|---|---|
| id | **bigint** | PK | Suporta alto volume |
| placa_detectada | varchar(10) | NOT NULL | Placa lida pela câmera |
| veiculo_id | integer | FK → veiculos, **NULL** | NULL se placa não cadastrada |
| camera_id | integer | FK → cameras, NOT NULL | Câmera que fez a leitura |
| autorizado | boolean | NOT NULL | true = acesso liberado |
| confianca | numeric | CHECK 0–100 | % de confiança do YOLO |
| imagem_url | text | NULL | Foto da placa capturada |
| motivo_bloqueio | varchar(255) | NULL | Preenchido se negado |
| tempo_processamento_ms | integer | NULL | Performance do ALPR |
| registrado_em | timestamp | DEFAULT now() | Momento do acesso |

---

### 2.9 autorizacoes_temporarias

Visitantes com acesso autorizado por período determinado. O sistema desativa automaticamente ao expirar via trigger.

| Coluna | Tipo | Descrição |
|---|---|---|
| estabelecimento_id | FK → estabelecimentos | Onde o acesso é válido |
| placa | varchar(10) NOT NULL | Placa do visitante |
| nome_autorizado | varchar(255) NOT NULL | Nome do visitante |
| autorizado_por | FK → pessoas, NULL | Quem autorizou |
| data_inicio / data_fim | timestamp NOT NULL | Período de validade |
| ativo | boolean DEFAULT true | Desativado automaticamente ao expirar |

---

### 2.10 usuarios_sistema

Usuários que fazem login no painel. Sempre vinculados a uma pessoa e a um perfil de acesso.

| Coluna | Tipo | Descrição |
|---|---|---|
| pessoa_id | FK → pessoas, UNIQUE | Uma pessoa = um usuário |
| estabelecimento_id | FK → estabelecimentos | Estabelecimento do usuário |
| perfil_acesso_id | FK → perfis_acesso | Nível de permissão |
| login | varchar(100) UNIQUE | Login único no sistema |
| senha_hash | varchar(255) NOT NULL | Senha (hash bcrypt em produção) |
| ultimo_acesso | timestamp NULL | Último login registrado |
| ativo | boolean DEFAULT true | Soft delete |

---

### 2.11 configuracoes

Pares chave-valor de configuração por estabelecimento. Permite personalizar comportamentos sem alterar código.

| Coluna | Tipo | Descrição |
|---|---|---|
| estabelecimento_id + chave | FK + varchar(100) UNIQUE | Chave única por estabelecimento |
| valor | text NOT NULL | Valor da configuração |
| descricao | varchar(255) | Explicação da configuração |
| atualizado_em | timestamp | Atualizado automaticamente via trigger |

---

### 2.12 imagens_treino

Armazena o dataset de imagens de placas utilizado para treinar o modelo YOLO. **Conecta o banco ao pipeline de Inteligência Artificial do projeto.**

| Coluna | Tipo | Descrição |
|---|---|---|
| imagem_url | text NOT NULL | URL da imagem no storage |
| placa_rotulo | varchar(10) | Placa correta (label do dataset) |
| largura / altura | integer | Dimensões em pixels |
| formato | varchar(10) | jpg, png, etc. |
| tamanho_bytes | integer | Peso do arquivo |
| dataset | varchar(50) DEFAULT 'treino' | treino / validacao / teste |
| qualidade | varchar(20) | boa / ruim / descartada |
| processada | boolean DEFAULT false | Se já foi usado no treino |

---

## 3. Views

As views encapsulam as consultas mais complexas e frequentes, simplificando o trabalho do frontend.

### 3.1 vw_placas_autorizadas

Retorna todas as placas com acesso ativo, com dados do proprietário, unidade e bloco. Usada pela câmera para verificar se um veículo pode entrar.

| Campo retornado | Origem | Uso |
|---|---|---|
| placa | veiculos.placa | Comparação com a câmera |
| proprietario | pessoas.nome | Nome do morador |
| cpf | pessoas.cpf | Identificação do proprietário |
| unidade | unidades.identificacao | Apartamento/sala |
| bloco | blocos.nome | Torre/bloco |
| veiculo_id / pessoa_id | IDs internos | Para joins adicionais |

---

### 3.2 vw_autorizacoes_ativas

Retorna somente autorizações temporárias que estão **ativas e dentro do prazo**. Usada para verificar visitantes autorizados.

| Campo retornado | Descrição |
|---|---|
| placa | Placa do visitante |
| nome_autorizado | Nome do visitante |
| motivo | Motivo da autorização |
| autorizado_por | Nome de quem autorizou |
| data_inicio / data_fim | Período de validade |
| estabelecimento | Qual condomínio |

---

### 3.3 vw_ultimos_acessos

Retorna o histórico de acessos com todos os detalhes em uma única consulta. Usada pelo **dashboard do painel**.

| Campo retornado | Descrição |
|---|---|
| id | ID do acesso |
| placa_detectada | Placa lida pela câmera |
| autorizado | true / false |
| motivo_bloqueio | Motivo se negado |
| confianca | % de precisão do YOLO |
| imagem_url | Foto da placa |
| tempo_processamento_ms | Velocidade do processamento |
| registrado_em | Data e hora |
| proprietario | Nome do dono do veículo |
| camera | Nome da câmera que registrou |

---

## 4. Functions (PL/pgSQL)

Toda a lógica de negócio crítica está centralizada no banco via PL/pgSQL, garantindo integridade independente do frontend.

### 4.1 registrar_acesso — Function principal

Chamada a cada leitura de placa pela câmera. Verifica se o veículo está cadastrado e registra o acesso no log.

**Parâmetros:**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| p_placa | varchar | Placa detectada pela câmera |
| p_camera_id | integer | ID da câmera que fez a leitura |
| p_confianca | numeric | Percentual de confiança do modelo YOLO (0–100) |
| p_imagem_url | text | URL da foto capturada (pode ser NULL) |
| p_tempo_ms | integer | Tempo de processamento em milissegundos |

**Retorno:** JSON com `acesso_id` (bigint) e `autorizado` (boolean)

**Fluxo interno:**
1. Busca o `veiculo_id` na tabela `veiculos` pela placa informada (se não encontrar, registra com `veiculo_id NULL`)
2. Insere um registro na tabela `acessos` com todos os dados recebidos
3. Retorna JSON com o ID do acesso gerado e o status de autorização

**Exemplo de chamada:**
```sql
SELECT registrar_acesso('ABC1D23', 1, 98.5, null, 120);
```

---

### 4.2 normalizar_placa

Converte automaticamente a placa para maiúsculo e remove espaços extras antes de salvar na tabela `veiculos`.

```
" abc1234 " → "ABC1234"
```

---

### 4.3 verificar_placa_duplicada

Impede cadastro de placa duplicada ativa. Se a mesma placa já estiver cadastrada com `ativo = true`, lança exceção antes de qualquer INSERT ou UPDATE.

```
RAISE EXCEPTION 'Placa ABC1234 já está cadastrada e ativa.'
```

---

### 4.4 desativar_autorizacoes_expiradas

Percorre a tabela `autorizacoes_temporarias` e seta `ativo = false` em todos os registros onde `data_fim < NOW()`. Chamada automaticamente via trigger após cada novo acesso registrado.

---

### 4.5 atualizar_timestamp

Atualiza o campo `atualizado_em` para `NOW()` sempre que um registro é editado. Usada pelos triggers das tabelas `veiculos`, `pessoas`, `estabelecimentos` e `configuracoes`.

---

## 5. Triggers

| Trigger | Tabela | Evento | Momento | Chama | O que faz |
|---|---|---|---|---|---|
| `trg_normalizar_placa_veiculo` | veiculos | INSERT / UPDATE | BEFORE | normalizar_placa | Converte placa para maiúsculo |
| `trg_placa_duplicada` | veiculos | INSERT / UPDATE | BEFORE | verificar_placa_duplicada | Bloqueia placa duplicada ativa |
| `trg_limpar_autorizacoes` | acessos | INSERT | AFTER | desativar_autorizacoes_expiradas | Limpa autorizações vencidas automaticamente |
| `trg_veiculos_updated` | veiculos | UPDATE | BEFORE | atualizar_timestamp | Atualiza atualizado_em |
| `trg_pessoas_updated` | pessoas | UPDATE | BEFORE | atualizar_timestamp | Atualiza atualizado_em |
| `trg_estabelecimentos_updated` | estabelecimentos | UPDATE | BEFORE | atualizar_timestamp | Atualiza atualizado_em |
| `trg_configuracoes_updated` | configuracoes | UPDATE | BEFORE | atualizar_timestamp | Atualiza atualizado_em |

---

## 6. Diagrama de Relacionamentos

```
[estabelecimentos]
       │
       ├──── [blocos] ──── [unidades] ──── [vinculos] ──── [pessoas] ──── [veiculos]
       │                                        │                │               │
       ├──── [cameras] ─────────── [acessos] ───┘               │               │
       │                               ↑                        │               │
       ├──── [autorizacoes_temporarias]─────────────────────────┘               │
       │                                                                         │
       ├──── [configuracoes]                                                     │
       │                                                                         │
       └──── [usuarios_sistema] ──── [perfis_acesso]                             │
                    │                                                             │
                    └──── pessoa_id ───────────────────────────────────────────-─┘

Tabelas de domínio:  tipos_camera | tipos_estabelecimento | tipos_veiculo | tipos_vinculo
Tabela de IA:        imagens_treino
```

**Cardinalidades:**

| Entidade pai | Entidade filha | Cardinalidade | Descrição |
|---|---|---|---|
| estabelecimentos | blocos | 1 → N | Um condomínio tem vários blocos |
| blocos | unidades | 1 → N | Um bloco tem várias unidades |
| unidades | vinculos | 1 → N | Uma unidade tem vários vínculos |
| pessoas | vinculos | 1 → N | Uma pessoa pode estar em várias unidades |
| pessoas | veiculos | 1 → N | Uma pessoa pode ter vários veículos |
| veiculos | acessos | 1 → N | Um veículo tem histórico de acessos |
| cameras | acessos | 1 → N | Uma câmera registra vários acessos |
| pessoas | autorizacoes_temporarias | 1 → N | Uma pessoa pode autorizar vários visitantes |
| pessoas | usuarios_sistema | 1 → 1 | Uma pessoa = um usuário do sistema |
| perfis_acesso | usuarios_sistema | 1 → N | Um perfil para vários usuários |

---

## 7. Tecnologias Utilizadas

| Tecnologia | Versão | Como foi usada |
|---|---|---|
| PostgreSQL | 17 | Banco de dados relacional principal |
| Supabase | BaaS | Hospedagem na nuvem, API REST e autenticação |
| SQL puro | — | Criação das tabelas, constraints, índices e CHECKs |
| PL/pgSQL | — | Functions e triggers de automação |
| @supabase/supabase-js | v2 | Client JavaScript para integração com o frontend |

---

*GateVision — Documentação do Banco de Dados*
