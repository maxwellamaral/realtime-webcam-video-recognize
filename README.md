# PyScript Realtime Webcam Vision

> Aplicação web para análise de vídeo em tempo real usando modelos de visão computacional (VLM) diretamente no navegador com PyScript.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-PyScript-blue)](https://pyscript.net/)
[![AI Assisted](https://img.shields.io/badge/AI%20Assisted-Antigravity-purple)]()

## Sobre

Este projeto permite capturar vídeo da webcam e enviá-lo para modelos de visão computacional (VLM) para análise em tempo real. Todo o código Python é executado diretamente no navegador usando **PyScript**, sem necessidade de backend.

### Inspiração

Este projeto foi inspirado no trabalho de **[smolvlm-realtime-webcam](https://github.com/ngxson/smolvlm-realtime-webcam)** por ngxson, porém com implementação diferente:

- **PyScript**: Código Python executando no navegador
- **LM Studio**: Backend local para inferência
- **Modelos testados**: `SmolVLM-500M-Instruct-GGUF`, `qwen3-vl-8b-instruct`

## Funcionalidades

### Webcam (Tempo Real)

| Funcionalidade           | Descrição                                         |
| ------------------------ | ------------------------------------------------- |
| 📹 **Captura de Webcam** | Acesso à câmera do dispositivo via navegador      |
| 🎥 **Seleção de Câmera** | Escolha entre múltiplas câmeras disponíveis       |
| 🤖 **Análise por VLM**   | Envio de frames para modelos de visão             |
| ⏱️ **Tempo Real**        | Processamento contínuo com intervalo configurável |
| 🎬 **Gravação de Vídeo** | Exportação do vídeo em formato WebM               |
| 📝 **Legendas SRT**      | Geração de legendas timestampadas                 |
| ⏸️ **Pause/Resume**      | Pausar e retomar webcam automaticamente           |

### Vídeo Local

| Funcionalidade             | Descrição                            |
| -------------------------- | ------------------------------------ |
| 📁 **Upload de Vídeo**     | Carregue vídeos do computador        |
| 🖱️ **Drag & Drop**         | Arraste e solte arquivos para upload |
| ▶️ **Player Completo**     | Play, pause, stop, seek, velocidade  |
| ⏮️ **Navegação por Frame** | Avance ou retroceda frame a frame    |
| 🔁 **Modo Loop**           | Repetição automática do vídeo        |
| ⌨️ **Atalhos de Teclado**  | Espaço (play/pause), setas (frames)  |
| 📝 **Legendas SRT**        | Geração de legendas sincronizadas    |

### Imagem Estática

| Funcionalidade          | Descrição                            |
| ----------------------- | ------------------------------------ |
| 📁 **Upload de Imagem** | Carregue imagens do computador       |
| 🖱️ **Drag & Drop**      | Arraste e solte arquivos para upload |
| 🔍 **Análise Única**    | Análise pontual da imagem carregada  |

### Interface

| Funcionalidade         | Descrição                               |
| ---------------------- | --------------------------------------- |
| 🎨 **Tema Escuro**     | Interface moderna com Pico CSS          |
| 📱 **Responsivo**      | Adaptável a diferentes tamanhos de tela |
| 🔄 **Sistema de Abas** | Navegação intuitiva entre modos         |

## Como Usar

### Pré-requisitos

1. **LM Studio** ou **llama.cpp** rodando localmente
2. Modelo de visão carregado (ex: `SmolVLM-500M-Instruct-GGUF`)
3. Navegador moderno com suporte a WebRTC

### Execução

```bash
# Clone o repositório
git clone https://github.com/maxwellamaral/realtime-webcam-video-recognize.git
cd realtime-webcam/src/

# Inicie um servidor HTTP local
python -m http.server 8000

# Acesse no navegador
# http://localhost:8000
```

### Configuração

1. Selecione o provedor (LM Studio ou llama.cpp)
2. Verifique a URL base da API
3. Digite uma instrução (ex: "What do you see?")
4. Opcionalmente, ative "Gravar vídeo com legendas"
5. Clique em **Start**

### Configurando o LM Studio

O LM Studio é uma aplicação desktop que permite executar modelos de linguagem localmente. Siga os passos abaixo para configurá-lo:

#### 1. Instalação

1. Baixe o LM Studio em [lmstudio.ai](https://lmstudio.ai/)
2. Instale e abra a aplicação

#### 2. Baixando Modelos VLM

Na aba **Discover**, pesquise e baixe um dos modelos de visão recomendados:

| Modelo                       | Tamanho | Descrição                                                    |
| ---------------------------- | ------- | ------------------------------------------------------------ |
| `SmolVLM-500M-Instruct-GGUF` | ~500MB  | Modelo leve, ideal para testes rápidos                       |
| `qwen2-vl-7b-instruct-GGUF`  | ~4-8GB  | Maior qualidade, requer mais recursos, funciona em português |

> 💡 **Dica**: Para o SmolVLM, pesquise por "SmolVLM" e selecione a versão GGUF quantizada (ex: Q4_K_M).

#### 3. Iniciando o Servidor

1. Vá para a aba **Local Server** (ícone de servidor no menu lateral)
2. Selecione o modelo VLM carregado
3. Configure as opções:
   - **Port**: 1234 (padrão)
   - **CORS**: Ativado (importante para requisições do navegador)
4. Clique em **Start Server**

#### 4. Verificando a API

O servidor deve estar rodando em `http://localhost:1234`. Você pode testar com:

```bash
curl http://localhost:1234/v1/models
```

#### 5. Configuração na Aplicação

Na aplicação web:

- **Provedor**: LM Studio
- **Base API**: `http://localhost:1234`

### Solução de Problemas

| Problema                   | Solução                                               |
| -------------------------- | ----------------------------------------------------- |
| CORS Error                 | Ative CORS nas configurações do servidor LM Studio    |
| Connection Refused         | Verifique se o servidor está rodando na porta correta |
| Modelo não suporta imagens | Use um modelo VLM (Vision Language Model)             |
| Resposta lenta             | Reduza o intervalo ou use um modelo menor             |

## Estrutura do Projeto

```
realtime-webcam/
├── src/
│   ├── index.html        # Página principal com sistema de abas
│   ├── camera_app.py     # Lógica Python (PyScript) - 9 classes
│   └── styles.css        # Estilos customizados
├── docs/
│   └── class_diagram.md  # Diagrama UML de classes
├── .gitignore            # Arquivos ignorados pelo Git
├── README.md             # Este arquivo
├── LICENSE               # Licença MIT
└── CITATION.bib          # Referência BibLaTeX
```

### Arquitetura de Classes

O código Python está organizado em 9 classes:

| Classe               | Responsabilidade               |
| -------------------- | ------------------------------ |
| `DOMElements`        | Cache de elementos HTML        |
| `AppState`           | Estado global da aplicação     |
| `APIClient`          | Comunicação com APIs de visão  |
| `CaptionGenerator`   | Geração de legendas SRT        |
| `WebcamManager`      | Gerenciamento da webcam        |
| `VideoPlayerManager` | Player de vídeo local          |
| `ImageAnalyzer`      | Análise de imagens             |
| `TabManager`         | Navegação entre abas           |
| `VisionApp`          | Classe principal orquestradora |

Veja o diagrama completo em [`docs/class_diagram.md`](docs/class_diagram.md).

## Tecnologias

- **[PyScript](https://pyscript.net/)** - Python no navegador
- **[Pico CSS](https://picocss.com/)** - Framework CSS minimalista
- **MediaRecorder API** - Gravação de vídeo
- **WebRTC** - Acesso à webcam
- **File API** - Upload de arquivos

## Citação

Se utilizar este projeto em trabalhos acadêmicos, por favor cite:

```bibtex
@software{pyscript_realtime_webcam_2025,
  author       = {Maxwell Amaral},
  title        = {{PyScript Realtime Webcam Vision: Real-time Video Analysis with Vision Language Models in the Browser}},
  year         = {2025},
  month        = dec,
  url          = {https://github.com/maxwellamaral/realtime-webcam-video-recognize},
  version      = {1.0.0},
  abstract     = {A web application for real-time video analysis using Vision Language Models (VLM) directly in the browser with PyScript. Features include webcam capture, configurable processing intervals, video recording with timestamped SRT captions, and support for LM Studio and llama.cpp backends.},
  keywords     = {pyscript, webcam, vision-language-models, real-time, browser, python, vlm, lm-studio, llama-cpp},
  note         = {AI-assisted development with Antigravity (Google DeepMind) with human review and professional supervision. Inspired by smolvlm-realtime-webcam by ngxson.}
}
```

## Desenvolvimento Assistido por IA

Este projeto foi desenvolvido utilizando **engenharia de software assistida por IA Generativa** (Antigravity by Google DeepMind), com:

- Supervisão e revisão humana
- Acompanhamento profissional
- Validação de boas práticas

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE) - veja o arquivo LICENSE para detalhes.

**Requisito**: Ao utilizar este código, mencione o autor original.

## Agradecimentos

- [ngxson](https://github.com/ngxson) pela inspiração do projeto original
- [PyScript](https://pyscript.net/) pela tecnologia
- [LM Studio](https://lmstudio.ai/) pela facilidade de uso de modelos locais
