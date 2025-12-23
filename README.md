# PyScript Realtime Webcam Vision

> Aplicação web para análise de vídeo em tempo real usando modelos de visão computacional (VLM) diretamente no navegador com PyScript.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-PyScript-blue)](https://pyscript.net/)
[![AI Assisted](https://img.shields.io/badge/AI%20Assisted-Antigravity-purple)]()

## 📖 Sobre

Este projeto permite capturar vídeo da webcam e enviá-lo para modelos de visão computacional (VLM) para análise em tempo real. Todo o código Python é executado diretamente no navegador usando **PyScript**, sem necessidade de backend.

### 🎯 Inspiração

Este projeto foi inspirado no trabalho de **[smolvlm-realtime-webcam](https://github.com/ngxson/smolvlm-realtime-webcam)** por ngxson, porém com implementação diferente:

- **PyScript**: Código Python executando no navegador
- **LM Studio**: Backend local para inferência
- **Modelos testados**: `SmolVLM-500M-Instruct-GGUF`, `qwen3-vl-8b-instruct`

## ✨ Funcionalidades

| Funcionalidade           | Descrição                                         |
| ------------------------ | ------------------------------------------------- |
| 📷 **Captura de Webcam** | Acesso à câmera do dispositivo via navegador      |
| 🤖 **Análise por VLM**   | Envio de frames para modelos de visão             |
| ⏱️ **Tempo Real**        | Processamento contínuo com intervalo configurável |
| 🎬 **Gravação de Vídeo** | Exportação do vídeo em formato WebM               |
| 📝 **Legendas SRT**      | Geração de legendas timestampadas                 |
| 🌙 **Tema Escuro**       | Interface moderna com Pico CSS                    |

## 🚀 Como Usar

### Pré-requisitos

1. **LM Studio** ou **llama.cpp** rodando localmente
2. Modelo de visão carregado (ex: `SmolVLM-500M-Instruct-GGUF`)
3. Navegador moderno com suporte a WebRTC

### Execução

```bash
# Clone o repositório
git clone <repo-url>
cd realtime-webcam

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

## 📁 Estrutura do Projeto

```
realtime-webcam/
├── src/
│   ├── index.html      # Página principal
│   ├── camera_app.py   # Lógica Python (PyScript)
│   └── styles.css      # Estilos customizados
├── README.md           # Este arquivo
├── LICENSE             # Licença MIT
└── CITATION.bib        # Referência BibLaTeX
```

## 🛠️ Tecnologias

- **[PyScript](https://pyscript.net/)** - Python no navegador
- **[Pico CSS](https://picocss.com/)** - Framework CSS minimalista
- **MediaRecorder API** - Gravação de vídeo
- **WebRTC** - Acesso à webcam

## 📚 Citação

Se utilizar este projeto em trabalhos acadêmicos, por favor cite:

```bibtex
@software{pyscript_realtime_webcam_2024,
  author       = {Maxwell Amaral},
  title        = {PyScript Realtime Webcam Vision},
  year         = {2024},
  url          = {https://github.com/maxwellamaral/realtime-webcam-video-recognize},
  note         = {AI-assisted development with Antigravity}
}
```

## 🤖 Desenvolvimento Assistido por IA

Este projeto foi desenvolvido utilizando **engenharia de software assistida por IA Generativa** (Antigravity by Google DeepMind), com:

- ✅ Supervisão e revisão humana
- ✅ Acompanhamento profissional
- ✅ Validação de boas práticas

O código gerado foi revisado, testado e ajustado por profissional qualificado.

## 📄 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE) - veja o arquivo LICENSE para detalhes.

**Requisito**: Ao utilizar este código, mencione o autor original.

## 🙏 Agradecimentos

- [ngxson](https://github.com/ngxson) pela inspiração do projeto original
- [PyScript](https://pyscript.net/) pela tecnologia
- [LM Studio](https://lmstudio.ai/) pela facilidade de uso de modelos locais
