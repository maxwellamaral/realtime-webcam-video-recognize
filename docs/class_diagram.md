# Diagrama UML de Classes - Vision AI

Este documento apresenta o diagrama de classes da aplicação Vision AI.

## Visão Geral da Arquitetura

```mermaid
classDiagram
    direction TB

    %% =========================================
    %% CLASSES PRINCIPAIS
    %% =========================================

    class VisionApp {
        <<Orquestrador>>
        +dom: DOMElements
        +state: AppState
        +api_client: APIClient
        +webcam: WebcamManager
        +video_player: VideoPlayerManager
        +image_analyzer: ImageAnalyzer
        +tab_manager: TabManager
        +__init__()
        +init() async
        +handle_start()
        +handle_stop()
        +toggle_processing(event)
        -_setup_drag_drop()
        -_setup_event_listeners()
        -_on_keydown(event)
        -_cleanup(event)
        -_send_data() async
        -_processing_loop() async
    }

    class DOMElements {
        <<Cache de Elementos>>
        +api_provider
        +base_url
        +instruction_text
        +response_text
        +start_button
        +video
        +canvas
        +camera_select
        +local_video
        +loaded_image
        +__init__()
    }

    class AppState {
        <<Estado Global>>
        +current_tab: str
        +stream: MediaStream
        +is_processing: bool
        +processing_task: Task
        +available_cameras: list
        +is_webcam_paused: bool
        +media_recorder: MediaRecorder
        +recorded_chunks: list
        +webcam_captions: list
        +video_captions: list
        +is_loop_enabled: bool
        +current_image_base64: str
        +__init__()
    }

    class APIClient {
        <<Comunicação HTTP>>
        +dom: DOMElements
        +__init__(dom)
        +update_base_url(event)
        +send_request(instruction, image_base64) async
    }

    class CaptionGenerator {
        <<Utilitário Estático>>
        +format_time_srt(seconds)$ str
        +format_time_display(seconds)$ str
        +generate_srt_content(captions_list)$ str
        +download_srt(captions_list, filename)$
    }

    class WebcamManager {
        <<Gerenciador de Webcam>>
        +dom: DOMElements
        +state: AppState
        +__init__(dom, state)
        +enumerate_cameras() async
        +switch_camera(device_id) async
        +on_camera_change(event)
        +init() async
        +capture_frame() str
        +pause()
        +resume() async
        +toggle(event)
        +start_recording()
        +stop_recording()
        +add_caption(text)
        +download_video(event)
        +download_captions(event)
    }

    class VideoPlayerManager {
        <<Player de Vídeo>>
        +dom: DOMElements
        +state: AppState
        +__init__(dom, state)
        +on_file_selected(event)
        +load_file(file)
        +on_loaded_metadata(event)
        +on_time_update(event)
        +on_timeline_change(event)
        +toggle_play_pause(event)
        +stop(event)
        +prev_frame(event)
        +next_frame(event)
        +rewind(event)
        +forward(event)
        +change_speed(event)
        +toggle_loop(event)
        +on_ended(event)
        +show_upload(event)
        +capture_frame() str
        +add_caption(text)
        +download_captions(event)
    }

    class ImageAnalyzer {
        <<Analisador de Imagem>>
        +dom: DOMElements
        +state: AppState
        +api_client: APIClient
        +__init__(dom, state, api_client)
        +on_file_selected(event)
        +load_file(file)
        +show_upload(event)
        +analyze() async
        +on_analyze_click(event)
    }

    class TabManager {
        <<Gerenciador de Abas>>
        +dom: DOMElements
        +state: AppState
        +webcam: WebcamManager
        +on_stop_callback: callable
        +__init__(dom, state, webcam)
        +set_stop_callback(callback)
        +switch(event)
    }

    %% =========================================
    %% RELACIONAMENTOS
    %% =========================================

    VisionApp *-- DOMElements : compõe
    VisionApp *-- AppState : compõe
    VisionApp *-- APIClient : compõe
    VisionApp *-- WebcamManager : compõe
    VisionApp *-- VideoPlayerManager : compõe
    VisionApp *-- ImageAnalyzer : compõe
    VisionApp *-- TabManager : compõe

    APIClient --> DOMElements : usa
    WebcamManager --> DOMElements : usa
    WebcamManager --> AppState : usa
    VideoPlayerManager --> DOMElements : usa
    VideoPlayerManager --> AppState : usa
    ImageAnalyzer --> DOMElements : usa
    ImageAnalyzer --> AppState : usa
    ImageAnalyzer --> APIClient : usa
    TabManager --> DOMElements : usa
    TabManager --> AppState : usa
    TabManager --> WebcamManager : usa

    WebcamManager ..> CaptionGenerator : utiliza
    VideoPlayerManager ..> CaptionGenerator : utiliza
```

## Descrição das Classes

| Classe                 | Responsabilidade                                             | Padrão            |
| ---------------------- | ------------------------------------------------------------ | ----------------- |
| **VisionApp**          | Orquestra toda a aplicação, inicializa e conecta componentes | Façade/Compositor |
| **DOMElements**        | Cache centralizado de elementos HTML                         | Singleton-like    |
| **AppState**           | Estado global da aplicação                                   | State Pattern     |
| **APIClient**          | Comunicação HTTP com APIs de visão                           | Service           |
| **CaptionGenerator**   | Utilitários estáticos para legendas SRT                      | Utility Class     |
| **WebcamManager**      | Gerencia webcam, gravação e captura                          | Manager Pattern   |
| **VideoPlayerManager** | Controles de player de vídeo                                 | Manager Pattern   |
| **ImageAnalyzer**      | Upload e análise de imagens                                  | Service           |
| **TabManager**         | Navegação e lógica de abas                                   | Controller        |

## Fluxo de Dependências

```mermaid
flowchart LR
    subgraph "Camada de Orquestração"
        VA[VisionApp]
    end

    subgraph "Camada de Gerenciamento"
        WM[WebcamManager]
        VP[VideoPlayerManager]
        IA[ImageAnalyzer]
        TM[TabManager]
    end

    subgraph "Camada de Infraestrutura"
        DOM[DOMElements]
        STATE[AppState]
        API[APIClient]
        CAP[CaptionGenerator]
    end

    VA --> WM
    VA --> VP
    VA --> IA
    VA --> TM

    WM --> DOM
    WM --> STATE
    WM -.-> CAP

    VP --> DOM
    VP --> STATE
    VP -.-> CAP

    IA --> DOM
    IA --> STATE
    IA --> API

    TM --> DOM
    TM --> STATE
    TM --> WM

    API --> DOM
```

## Legenda

- **Linha sólida (-->)**: Dependência forte (injeção de dependência)
- **Linha tracejada (..>)**: Uso ocasional (métodos estáticos)
- **Composição (\*--)**: VisionApp cria e gerencia as instâncias
