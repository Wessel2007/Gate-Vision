<h1 align="center">GateVision</h1>

<p align="center">
Sistema Inteligente de Abertura de Portão por Reconhecimento de Placas
</p>

<p align="center">
<img src="https://img.shields.io/badge/status-em%20desenvolvimento-green?style=for-the-badge"/>
<img src="https://img.shields.io/badge/python-vision%20system-blue?style=for-the-badge"/>
<img src="https://img.shields.io/badge/arduino-hardware-orange?style=for-the-badge"/>
</p>

---

# Índice

- [Descrição do Projeto](#descrição-do-projeto)
- [Status do Projeto](#status-do-projeto)
- [Funcionalidades](#funcionalidades)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Acesso ao Projeto](#acesso-ao-projeto)
- [Executar o Projeto](#executar-o-projeto)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvedores](#desenvolvedores)
- [Licença](#licença)

---

# Descrição do Projeto

O **GateVision** é um sistema de automação para controle de acesso de veículos utilizando **visão computacional** e **reconhecimento de placas**.

O sistema utiliza uma câmera para capturar imagens dos veículos que chegam ao portão. A partir dessas imagens, um modelo **YOLO** treinado identifica e recorta a região da placa do veículo. Em seguida, o texto da placa é extraído por OCR e verificado em um banco de dados.

Caso a placa esteja autorizada, um comando é enviado para um **Arduino**, que aciona um **servo motor responsável pela abertura do portão**.

O projeto integra conceitos de:

- Inteligência Artificial
- Visão Computacional
- Banco de Dados
- Automação com Arduino
- Desenvolvimento Web

---

# Status do Projeto

**Projeto em desenvolvimento**

Período de desenvolvimento:

**Fevereiro de 2026 – Junho de 2026**

### O que já está implementado

- [x] Detecção de placas em imagens com modelo YOLO treinado (`models/best.pt`)
- [x] Recorte automático da região da placa detectada

### Próximas etapas

- [ ] OCR para leitura dos caracteres da placa
- [ ] Captura em tempo real via webcam
- [ ] Banco de dados de placas autorizadas (SQLite)
- [ ] Comunicação serial com Arduino
- [ ] Interface web para cadastro de placas
- [ ] Código do Arduino para acionamento do servo motor

---

# Funcionalidades

- `Detecção de placas`: identificação da região da placa em imagens usando YOLO
- `Recorte da placa`: extração da área detectada para processamento posterior
- `Reconhecimento de caracteres` *(planejado)*: leitura do texto da placa via OCR
- `Captura em tempo real` *(planejado)*: utilização de webcam para captura contínua
- `Validação de acesso` *(planejado)*: consulta da placa em banco de dados
- `Automação de portão` *(planejado)*: acionamento automático via Arduino
- `Interface web` *(planejado)*: cadastro de placas autorizadas

---

# Arquitetura do Sistema

Fluxo de funcionamento do sistema:

1. A webcam captura a imagem do veículo.
2. O sistema em Python processa a imagem.
3. O modelo YOLO detecta a região da placa.
4. A imagem da placa é recortada.
5. Um sistema de OCR extrai os caracteres.
6. O banco de dados é consultado.
7. Caso a placa esteja cadastrada:
   - Um comando é enviado via comunicação serial.
8. O Arduino recebe o comando.
9. O servo motor é acionado simulando a abertura do portão.

---

# Tecnologias Utilizadas

## Linguagens

- Python
- C++ (Arduino)
- HTML / CSS

## Bibliotecas

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) — detecção de objetos (YOLOv11)
- [OpenCV](https://opencv.org/) — processamento de imagens
- [PyTorch](https://pytorch.org/) — backend do modelo YOLO
- [NumPy](https://numpy.org/) — manipulação de arrays
- SQLite3 *(planejado)* — banco de dados local

## Hardware

- Webcam
- Arduino
- Servo Motor
- Notebook

## Ferramentas

- Arduino IDE
- Python 3.x

---

# Acesso ao Projeto

Você pode acessar o repositório do projeto através do GitHub:



---

# Executar o Projeto

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd deteccao-placas-veiculares
```

### 2. Criar e ativar ambiente virtual (recomendado)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

> **Nota:** a instalação do PyTorch pode variar conforme o sistema e a presença de GPU. Consulte [pytorch.org](https://pytorch.org/get-started/locally/) se necessário.

### 4. Executar a detecção em uma imagem

```bash
python src/detect.py
```

O resultado será salvo automaticamente na pasta `runs/` gerada pelo YOLO.

### 5. Recortar a região da placa detectada

```bash
python src/crop.py
```

O recorte será salvo como `placa_recortada.jpg` no diretório raiz.

### 6. Configurar Arduino *(etapa futura)*

1. Conectar o Arduino via USB
2. Abrir o Arduino IDE
3. Carregar o arquivo de controle do servo *(em desenvolvimento)*
4. Fazer upload do arquivo para o Arduino

---

# Estrutura do Projeto

<pre>
deteccao-placas-veiculares/
│
├── models/
│   └── best.pt               # Modelo YOLO treinado para detecção de placas
│
├── samples/
│   └── teste.jpg             # Imagem de exemplo para testes
│
├── src/
│   ├── detect.py             # Detecção de placas em imagem com YOLO
│   └── crop.py               # Recorte da região da placa detectada
│
├── requirements.txt          # Dependências do projeto
├── .gitignore
└── README.md
</pre>

---

# Desenvolvedores

| [<img src="https://avatars.githubusercontent.com/u/225480160?v=4" width=115><br><sub>Roger Oliveira</sub>](https://github.com/rcoliveirasb) |
| :---: |

| [<img src="https://avatars.githubusercontent.com/u/172124844?v=4" width=115><br><sub>Arthur Nicolas</sub>](https://github.com/arthur04112006) |
| :---: |

| [<img src="https://avatars.githubusercontent.com/u/199864121?v=4" width=115><br><sub>Kauan</sub>](https://github.com/kauanLDD) |
| :---: |

| [<img src="https://avatars.githubusercontent.com/u/217982820?v=4" width=115><br><sub>Rafael</sub>](https://github.com/rodyneyh) |
| :---: |

| [<img src="https://avatars.githubusercontent.com/u/217985092?v=4" width=115><br><sub>Lucas</sub>](https://github.com/lucas-labgit) |
| :---: |

| [<img src="https://avatars.githubusercontent.com/u/137013359?v=4" width=115><br><sub>Luiz Wessel</sub>](https://github.com/Wessel2007) |
| :---: |

Estudantes de Inteligência Artificial.

---

# Licença

Projeto desenvolvido para fins **acadêmicos e educacionais**.

Todos os direitos reservados ©.
