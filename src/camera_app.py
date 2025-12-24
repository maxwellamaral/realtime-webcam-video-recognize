"""
Vision AI - PyScript Application
=================================

Aplicação web para análise de vídeo e imagem em tempo real usando 
modelos de visão computacional (VLM - Vision Language Models).

Descrição:
    Este módulo é a camada de lógica Python da aplicação Vision AI.
    Ele utiliza PyScript para executar Python diretamente no navegador,
    fazendo ponte com APIs JavaScript nativas como:
    - MediaDevices API (acesso à webcam)
    - MediaRecorder API (gravação de vídeo)
    - File API (upload de arquivos)
    - Fetch API (requisições HTTP)

Funcionalidades:
    1. Webcam em Tempo Real: Captura e análise contínua de frames
    2. Vídeo Local: Player completo com controles e análise
    3. Imagem Estática: Upload e análise única de imagens
    4. Legendas SRT: Geração automática de legendas timestampadas

Arquitetura de Classes:
    - DOMElements: Referências centralizadas aos elementos HTML
    - AppState: Estado global da aplicação (padrão Singleton)
    - APIClient: Comunicação com APIs de visão (LM Studio, llama.cpp)
    - CaptionGenerator: Utilitários para geração de legendas SRT
    - WebcamManager: Gerenciamento completo da webcam
    - VideoPlayerManager: Controles de player de vídeo
    - ImageAnalyzer: Análise de imagens estáticas
    - TabManager: Navegação e lógica de abas
    - VisionApp: Classe orquestradora principal

Requisitos:
    - PyScript 2024.11.1+
    - Navegador com suporte a WebRTC
    - LM Studio ou llama.cpp rodando localmente

Autor: Maxwell Amaral
Versão: 1.0.0
Data: Dezembro 2025
Licença: MIT

Nota sobre IA:
    Este código foi desenvolvido com auxílio de IA Generativa (Antigravity)
    com revisão e supervisão humana profissional.
"""

# =============================================================================
# IMPORTS
# =============================================================================

# --- Módulos JavaScript via PyScript ---
# document: Manipulação do DOM HTML
# navigator: Acesso a APIs do navegador (câmera, etc.)
# console: Log de debug no console do navegador
# JSON: Serialização/deserialização JSON
# Object: Criação de objetos JavaScript
# window: Objeto global do navegador
# fetch: Requisições HTTP assíncronas
# Blob: Manipulação de dados binários
# URL: Criação de URLs de objetos
# FileReader: Leitura de arquivos do usuário
from js import document, navigator, console, JSON, Object, window, fetch, Blob, URL, FileReader

# --- Utilitários PyScript ---
# create_proxy: Converte funções Python em callbacks JavaScript
# to_js: Converte objetos Python para JavaScript
from pyodide.ffi import create_proxy, to_js

# --- Módulos Python padrão ---
import asyncio  # Operações assíncronas (async/await)
import json     # Parsing de respostas JSON


# =============================================================================
# CLASSE: DOMElements
# =============================================================================
class DOMElements:
    """
    Centraliza todas as referências aos elementos do DOM.
    
    Esta classe atua como um "cache" de elementos HTML, obtendo-os uma única
    vez durante a inicialização. Isso evita chamadas repetidas a getElementById
    e facilita a manutenção - todas as referências ficam em um só lugar.
    
    Organização:
        Os elementos são agrupados por funcionalidade:
        - Controles comuns: compartilhados entre todas as abas
        - Webcam: elementos específicos da captura de vídeo ao vivo
        - Vídeo local: elementos do player de vídeo
        - Imagem: elementos para visualização de imagens
    
    Uso:
        dom = DOMElements()
        dom.video.play()  # Acessa o elemento <video>
    """
    
    def __init__(self):
        """
        Inicializa todas as referências aos elementos do DOM.
        
        Cada atributo corresponde a um elemento HTML identificado por seu ID.
        Se um elemento não existir, o valor será None (comportamento do getElementById).
        """
        # --- Controles Comuns (compartilhados entre abas) ---
        self.api_provider = document.getElementById('apiProvider')         # <select> Provedor API
        self.base_url = document.getElementById('baseURL')                 # <input> URL da API
        self.instruction_text = document.getElementById('instructionText') # <textarea> Instrução
        self.response_text = document.getElementById('responseText')       # <textarea> Resposta
        self.interval_select = document.getElementById('intervalSelect')   # <select> Intervalo
        self.start_button = document.getElementById('startButton')         # <button> Start/Stop
        self.loading_overlay = document.getElementById('loadingOverlay')   # <div> Overlay loading
        
        # --- Webcam ---
        self.video = document.getElementById('videoFeed')                  # <video> Feed da webcam
        self.canvas = document.getElementById('canvas')                    # <canvas> Captura frame
        self.camera_select = document.getElementById('cameraSelect')       # <select> Seleção câmera
        self.enable_recording = document.getElementById('enableRecording') # <input> Checkbox gravação
        self.recording_indicator = document.getElementById('recordingIndicator')  # <span> Indicador REC
        self.download_section = document.getElementById('downloadSection') # <div> Seção downloads
        self.download_video_btn = document.getElementById('downloadVideo') # <button> Download vídeo
        self.download_captions_btn = document.getElementById('downloadCaptions')  # <button> Download SRT
        self.toggle_webcam_btn = document.getElementById('toggleWebcam')   # <button> Pausar/Retomar
        
        # --- Vídeo Local ---
        self.video_file_input = document.getElementById('videoFileInput')  # <input type="file">
        self.video_drop_zone = document.getElementById('videoDropZone')    # <div> Área drag & drop
        self.video_player_container = document.getElementById('videoPlayerContainer')  # <div> Container
        self.local_video = document.getElementById('localVideo')           # <video> Player vídeo
        self.local_video_canvas = document.getElementById('localVideoCanvas')  # <canvas> Captura
        self.video_timeline = document.getElementById('videoTimeline')     # <input range> Timeline
        self.current_time_display = document.getElementById('currentTime') # <span> Tempo atual
        self.total_time_display = document.getElementById('totalTime')     # <span> Duração total
        self.play_pause_btn = document.getElementById('playPause')         # <button> Play/Pause
        self.stop_video_btn = document.getElementById('stopVideo')         # <button> Stop
        self.prev_frame_btn = document.getElementById('prevFrame')         # <button> Frame anterior
        self.next_frame_btn = document.getElementById('nextFrame')         # <button> Próximo frame
        self.rewind_btn = document.getElementById('rewind')                # <button> Retroceder 5s
        self.forward_btn = document.getElementById('forward')              # <button> Avançar 5s
        self.playback_speed_select = document.getElementById('playbackSpeed')  # <select> Velocidade
        self.change_video_btn = document.getElementById('changeVideo')     # <button> Trocar vídeo
        self.video_download_section = document.getElementById('videoDownloadSection')  # <div>
        self.download_video_srt_btn = document.getElementById('downloadVideoSrt')  # <button> SRT
        self.toggle_loop_btn = document.getElementById('toggleLoop')       # <button> Loop
        
        # --- Imagem ---
        self.image_file_input = document.getElementById('imageFileInput')  # <input type="file">
        self.image_drop_zone = document.getElementById('imageDropZone')    # <div> Área drag & drop
        self.image_viewer_container = document.getElementById('imageViewerContainer')  # <div>
        self.loaded_image = document.getElementById('loadedImage')         # <img> Imagem carregada
        self.image_canvas = document.getElementById('imageCanvas')         # <canvas> (reservado)
        self.analyze_image_btn = document.getElementById('analyzeImage')   # <button> Analisar
        self.change_image_btn = document.getElementById('changeImage')     # <button> Trocar imagem


# =============================================================================
# CLASSE: AppState
# =============================================================================
class AppState:
    """
    Gerencia todo o estado global da aplicação.
    
    Esta classe centraliza todas as variáveis de estado, facilitando:
    - Debugging: todas as variáveis estão em um único lugar
    - Persistência: possibilidade de serializar/restaurar estado
    - Testes: fácil de mockar ou resetar estado
    
    O estado é dividido em categorias:
        - Estado de navegação: aba atual
        - Estado da webcam: stream, câmeras, flags
        - Estado de gravação: MediaRecorder, chunks, legendas
        - Estado de vídeo local: legendas, tempo
        - Estado de imagem: dados base64 da imagem
    
    Atributos:
        current_tab (str): Aba ativa ("webcam", "video", "image")
        stream (MediaStream | None): Stream da webcam ativo
        is_processing (bool): Se está processando frames
        processing_task (Task | None): Task assíncrona do loop de processamento
        available_cameras (list): Lista de câmeras detectadas
        is_webcam_paused (bool): Se webcam está pausada manualmente
        media_recorder (MediaRecorder | None): Gravador de vídeo
        recorded_chunks (list): Chunks de vídeo gravados
        webcam_captions (list): Legendas geradas durante gravação
        recording_start_time (float | None): Timestamp do início da gravação
        last_caption_time (float | None): Timestamp da última legenda
        video_captions (list): Legendas do vídeo local
        video_last_caption_time (float | None): Timestamp última legenda vídeo
        is_loop_enabled (bool): Se repetição do vídeo está ativa
        current_image_base64 (str | None): Imagem carregada em base64
    """
    
    def __init__(self):
        """Inicializa o estado com valores padrão."""
        # --- Estado de Navegação ---
        self.current_tab = "webcam"  # Aba inicial
        
        # --- Estado da Webcam ---
        self.stream = None                # MediaStream da câmera
        self.is_processing = False        # Flag: processando frames?
        self.processing_task = None       # asyncio.Task do loop
        self.available_cameras = []       # [{deviceId, label}, ...]
        self.is_webcam_paused = False     # Pausada manualmente?
        
        # --- Estado de Gravação ---
        self.media_recorder = None        # MediaRecorder API
        self.recorded_chunks = []         # Blob[] de vídeo
        self.webcam_captions = []         # [{start, end, text}, ...]
        self.recording_start_time = None  # window.performance.now() / 1000
        self.last_caption_time = None     # Último timestamp de legenda
        
        # --- Estado de Vídeo Local ---
        self.video_captions = []          # [{start, end, text}, ...]
        self.video_last_caption_time = None
        self.is_loop_enabled = False      # Repetir vídeo?
        
        # --- Estado de Imagem ---
        self.current_image_base64 = None  # "data:image/...;base64,..."


# =============================================================================
# CLASSE: APIClient
# =============================================================================
class APIClient:
    """
    Gerencia comunicação com APIs de visão computacional.
    
    Esta classe encapsula toda a lógica de comunicação HTTP com
    servidores de modelos de linguagem visual (VLM). Suporta:
    - LM Studio (porta padrão 1234)
    - llama.cpp (porta padrão 8080)
    
    O protocolo usado é o OpenAI Chat Completions API, que ambos
    os servidores implementam:
        POST /v1/chat/completions
        {
            "messages": [{"role": "user", "content": [...]}],
            "max_tokens": 100
        }
    
    Atributos:
        dom (DOMElements): Referência aos elementos do DOM
    
    Exemplo:
        client = APIClient(dom)
        response = await client.send_request("Descreva a imagem", image_base64)
    """
    
    def __init__(self, dom: DOMElements):
        """
        Inicializa o cliente de API.
        
        Args:
            dom: Instância de DOMElements para acessar campos de configuração
        """
        self.dom = dom
    
    def update_base_url(self, event):
        """
        Atualiza a URL base quando o provedor de API muda.
        
        Este callback é acionado quando o usuário altera o <select>
        de provedor. Define URLs padrão conhecidas para cada provedor.
        
        Args:
            event: Evento JavaScript do onChange
        
        Mapeamento:
            - 'llamacpp' -> http://localhost:8080
            - 'lmstudio' -> http://localhost:1234
        """
        provider = self.dom.api_provider.value
        if provider == 'llamacpp':
            self.dom.base_url.value = 'http://localhost:8080'
        elif provider == 'lmstudio':
            self.dom.base_url.value = 'http://localhost:1234'
    
    async def send_request(self, instruction: str, image_base64_url: str) -> str:
        """
        Envia requisição para a API de chat completion com imagem.
        
        Constrói uma requisição multimodal (texto + imagem) seguindo
        o formato da OpenAI Vision API. A imagem é enviada como
        URL data:image/... em base64.
        
        Args:
            instruction: Texto de instrução/prompt para o modelo
            image_base64_url: Imagem em formato "data:image/jpeg;base64,..."
        
        Returns:
            str: Resposta do modelo ou mensagem de erro
        
        Raises:
            Não levanta exceções - retorna string de erro em caso de falha
        
        Exemplo de payload enviado:
            {
                "max_tokens": 100,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "O que você vê?"},
                        {"type": "image_url", "image_url": {"url": "data:..."}}
                    ]
                }]
            }
        """
        try:
            url = f"{self.dom.base_url.value}/v1/chat/completions"
            
            # Monta o payload no formato OpenAI Vision
            payload = {
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instruction},
                            {"type": "image_url", "image_url": {"url": image_base64_url}}
                        ]
                    }
                ]
            }
            
            # Converte Python dict para JavaScript Object
            js_payload = to_js(payload, dict_converter=Object.fromEntries)
            headers = to_js({"Content-Type": "application/json"}, dict_converter=Object.fromEntries)
            
            options = to_js({
                "method": "POST",
                "headers": headers,
                "body": JSON.stringify(js_payload)
            }, dict_converter=Object.fromEntries)
            
            # Faz a requisição assíncrona
            response = await fetch(url, options)
            
            # Trata erros HTTP
            if not response.ok:
                status = response.status
                error_msg = f"Server error: {status}"
                if status == 404:
                    error_msg += " - Endpoint not found."
                elif status == 500:
                    error_msg += " - Server error."
                elif status in [400, 422]:
                    error_msg += " - Invalid request format."
                return error_msg
            
            # Parseia resposta JSON
            data_text = await response.text()
            data = json.loads(data_text)
            
            # Valida estrutura da resposta
            if 'choices' not in data or len(data['choices']) == 0:
                return "Error: Invalid response format"
            if 'message' not in data['choices'][0]:
                return "Error: Invalid response format"
            
            # Extrai e retorna o conteúdo da resposta
            return data['choices'][0]['message']['content']
            
        except Exception as e:
            console.log(f"Error in request: {str(e)}")
            return f"Error: {str(e)}"


# =============================================================================
# CLASSE: CaptionGenerator
# =============================================================================
class CaptionGenerator:
    """
    Utilitários para geração e download de legendas no formato SRT.
    
    Esta classe contém apenas métodos estáticos, funcionando como um
    "namespace" para funções relacionadas a legendas. O formato SRT
    (SubRip Text) é amplamente suportado por players de vídeo.
    
    Formato SRT:
        Cada legenda segue a estrutura:
        ```
        1
        00:00:01,000 --> 00:00:04,000
        Texto da primeira legenda
        
        2
        00:00:05,000 --> 00:00:08,000
        Texto da segunda legenda
        ```
    
    Estrutura de dados de legenda:
        Cada legenda é um dict com:
        - start (float): Tempo inicial em segundos
        - end (float): Tempo final em segundos
        - text (str): Texto da legenda
    
    Métodos:
        format_time_srt: Converte segundos para formato SRT
        format_time_display: Converte segundos para exibição MM:SS
        generate_srt_content: Gera string SRT completa
        download_srt: Dispara download de arquivo .srt
    """
    
    @staticmethod
    def format_time_srt(seconds: float) -> str:
        """
        Formata tempo em segundos para formato SRT.
        
        O formato SRT usa HH:MM:SS,mmm (vírgula como separador
        de milissegundos, não ponto).
        
        Args:
            seconds: Tempo em segundos (ex: 65.5)
        
        Returns:
            String formatada (ex: "00:01:05,500")
        
        Exemplo:
            >>> CaptionGenerator.format_time_srt(125.750)
            "00:02:05,750"
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    @staticmethod
    def format_time_display(seconds: float) -> str:
        """
        Formata tempo para exibição simples em player.
        
        Formato compacto MM:SS para mostrar no UI.
        
        Args:
            seconds: Tempo em segundos
        
        Returns:
            String formatada (ex: "02:35")
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def generate_srt_content(captions_list: list) -> str:
        """
        Gera conteúdo de arquivo SRT a partir de lista de legendas.
        
        Itera sobre a lista de legendas e formata cada uma seguindo
        a especificação SRT: número, timestamps, texto, linha vazia.
        
        Args:
            captions_list: Lista de dicts com keys 'start', 'end', 'text'
        
        Returns:
            String completa pronta para salvar como arquivo .srt
        
        Exemplo:
            >>> captions = [
            ...     {"start": 0, "end": 2.5, "text": "Olá"},
            ...     {"start": 3, "end": 5, "text": "Mundo"}
            ... ]
            >>> print(CaptionGenerator.generate_srt_content(captions))
            1
            00:00:00,000 --> 00:00:02,500
            Olá
            
            2
            00:00:03,000 --> 00:00:05,000
            Mundo
        """
        srt_lines = []
        
        for i, caption in enumerate(captions_list, 1):
            start = CaptionGenerator.format_time_srt(caption["start"])
            end = CaptionGenerator.format_time_srt(caption["end"])
            text = caption["text"]
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")  # Linha vazia entre legendas
        
        return "\n".join(srt_lines)
    
    @staticmethod
    def download_srt(captions_list: list, filename: str):
        """
        Dispara download de arquivo SRT no navegador.
        
        Cria um Blob com o conteúdo SRT, gera uma URL temporária,
        e simula um clique em link de download.
        
        Args:
            captions_list: Lista de legendas a exportar
            filename: Nome do arquivo para download (ex: "video.srt")
        
        Note:
            Se a lista estiver vazia, mostra alerta e não faz download.
        """
        if len(captions_list) == 0:
            window.alert("Nenhuma legenda gerada!")
            return
        
        srt_content = CaptionGenerator.generate_srt_content(captions_list)
        
        # Cria Blob com o conteúdo text/plain
        blob = Blob.new(
            to_js([srt_content]),
            to_js({"type": "text/plain"}, dict_converter=Object.fromEntries)
        )
        
        # Cria URL temporária e dispara download
        url = URL.createObjectURL(blob)
        a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)  # Libera memória


# =============================================================================
# CLASSE: WebcamManager
# =============================================================================
class WebcamManager:
    """
    Gerencia webcam, gravação de vídeo e captura de frames.
    
    Esta classe encapsula toda a interação com a câmera do dispositivo,
    incluindo:
    - Enumeração de dispositivos de vídeo disponíveis
    - Seleção e troca de câmera ativa
    - Captura de frames individuais como base64
    - Gravação contínua de vídeo com MediaRecorder
    - Geração de legendas sincronizadas durante gravação
    
    A classe utiliza a MediaDevices API do navegador para acessar
    a webcam e a MediaRecorder API para gravação.
    
    Atributos:
        dom (DOMElements): Referência aos elementos do DOM
        state (AppState): Estado compartilhado da aplicação
    
    Fluxo típico de uso:
        1. init() - Enumera câmeras e inicia a primeira encontrada
        2. capture_frame() - Captura frames durante processamento
        3. start_recording() / stop_recording() - Gravação opcional
    
    Exemplo:
        webcam = WebcamManager(dom, state)
        await webcam.init()
        frame = webcam.capture_frame()  # Returns "data:image/jpeg;base64,..."
    """
    
    def __init__(self, dom: DOMElements, state: AppState):
        """
        Inicializa o gerenciador de webcam.
        
        Args:
            dom: Instância de DOMElements para manipulação do DOM
            state: Instância de AppState para estado compartilhado
        """
        self.dom = dom
        self.state = state
    
    async def enumerate_cameras(self):
        """
        Enumera todas as câmeras de vídeo disponíveis no dispositivo.
        
        Este método usa a MediaDevices API para listar dispositivos.
        Primeiro solicita permissão temporária (necessário para obter
        os labels dos dispositivos), depois enumera e popula o <select>.
        
        Side Effects:
            - Limpa e repopula self.dom.camera_select
            - Atualiza self.state.available_cameras
            - Faz logs no console do navegador
        
        Raises:
            Não levanta exceções - trata erros internamente e mostra no UI
        """
        console.log("Starting camera enumeration...")
        
        try:
            # Limpa opções existentes
            while self.dom.camera_select.options.length > 0:
                self.dom.camera_select.remove(0)
            
            # Solicita permissão temporária para obter labels
            console.log("Requesting camera permission...")
            temp_constraints = to_js({"video": True, "audio": False}, dict_converter=Object.fromEntries)
            temp_stream = await navigator.mediaDevices.getUserMedia(temp_constraints)
            
            # Para o stream temporário imediatamente
            console.log("Permission granted, stopping temp stream...")
            tracks = temp_stream.getTracks()
            for i in range(tracks.length):
                tracks[i].stop()
            
            # Enumera todos os dispositivos
            console.log("Enumerating devices...")
            devices = await navigator.mediaDevices.enumerateDevices()
            console.log(f"Total devices found: {devices.length}")
            
            self.state.available_cameras = []
            
            # Filtra apenas dispositivos de vídeo
            for i in range(devices.length):
                device = devices[i]
                if device.kind == "videoinput":
                    device_id = device.deviceId
                    label = device.label if device.label else f"Câmera {len(self.state.available_cameras) + 1}"
                    
                    self.state.available_cameras.append({
                        "deviceId": device_id,
                        "label": label
                    })
                    
                    # Adiciona opção ao <select>
                    option = document.createElement("option")
                    option.value = device_id
                    option.textContent = label
                    self.dom.camera_select.appendChild(option)
                    console.log(f"Added camera: {label}")
            
            console.log(f"Found {len(self.state.available_cameras)} camera(s)")
            
            # Fallback se nenhuma câmera encontrada
            if len(self.state.available_cameras) == 0:
                option = document.createElement("option")
                option.value = ""
                option.textContent = "Nenhuma câmera encontrada"
                self.dom.camera_select.appendChild(option)
                
        except Exception as e:
            console.error(f"Error enumerating cameras: {str(e)}")
            while self.dom.camera_select.options.length > 0:
                self.dom.camera_select.remove(0)
            option = document.createElement("option")
            option.value = ""
            option.textContent = f"Erro: {str(e)}"
            self.dom.camera_select.appendChild(option)
    
    async def switch_camera(self, device_id: str = None):
        """
        Troca para uma câmera específica pelo seu deviceId.
        
        Para o stream atual (se houver) e inicia um novo com a
        câmera especificada. Se device_id for None, usa qualquer
        câmera disponível.
        
        Args:
            device_id: ID do dispositivo de vídeo (opcional)
        
        Side Effects:
            - Para tracks do stream atual
            - Cria novo stream e associa ao <video>
            - Atualiza self.state.stream
            - Mostra feedback no campo de resposta
        """
        try:
            # Para stream atual se existir
            if self.state.stream:
                tracks = self.state.stream.getTracks()
                for i in range(tracks.length):
                    tracks[i].stop()
            
            # Monta constraints com deviceId específico ou genérico
            if device_id:
                video_constraints = to_js({
                    "deviceId": {"exact": device_id}
                }, dict_converter=Object.fromEntries)
            else:
                video_constraints = True
            
            constraints = to_js({
                "video": video_constraints,
                "audio": False
            }, dict_converter=Object.fromEntries)
            
            # Obtém novo stream e conecta ao elemento <video>
            self.state.stream = await navigator.mediaDevices.getUserMedia(constraints)
            self.dom.video.srcObject = self.state.stream
            
            self.dom.response_text.value = "Câmera alterada com sucesso."
            console.log(f"Switched to camera: {device_id}")
            
        except Exception as e:
            error_msg = f"Erro ao trocar câmera: {str(e)}"
            console.error(error_msg)
            self.dom.response_text.value = error_msg
    
    def on_camera_change(self, event):
        """
        Callback acionado quando usuário seleciona outra câmera no <select>.
        
        Args:
            event: Evento JavaScript do onChange
        """
        device_id = self.dom.camera_select.value
        if device_id:
            asyncio.ensure_future(self.switch_camera(device_id))
    
    async def init(self):
        """
        Inicializa a webcam no carregamento da aplicação.
        
        Enumera câmeras disponíveis e ativa a primeira encontrada.
        Este método deve ser chamado uma vez, durante inicialização.
        """
        try:
            await self.enumerate_cameras()
            
            if len(self.state.available_cameras) > 0:
                first_camera_id = self.state.available_cameras[0]["deviceId"]
                await self.switch_camera(first_camera_id)
                self.dom.response_text.value = "Câmera inicializada. Pronto para começar."
            else:
                self.dom.response_text.value = "Nenhuma câmera encontrada."
            
            console.log("Camera initialized successfully")
            
        except Exception as e:
            error_msg = f"Error accessing camera: {str(e)}"
            console.error(error_msg)
            self.dom.response_text.value = error_msg
    
    def capture_frame(self) -> str:
        """
        Captura o frame atual da webcam como imagem base64.
        
        Usa um <canvas> oculto para desenhar o frame do <video>
        e exportar como data URL JPEG.
        
        Returns:
            String "data:image/jpeg;base64,..." ou None se não houver stream
        """
        if self.state.stream is None or self.dom.video.videoWidth == 0:
            return None
        
        # Configura canvas com dimensões do vídeo
        self.dom.canvas.width = self.dom.video.videoWidth
        self.dom.canvas.height = self.dom.video.videoHeight
        context = self.dom.canvas.getContext('2d')
        
        # Desenha frame atual e exporta como base64
        context.drawImage(self.dom.video, 0, 0, self.dom.canvas.width, self.dom.canvas.height)
        return self.dom.canvas.toDataURL('image/jpeg', 0.8)  # 80% quality
    
    def pause(self):
        """
        Pausa a webcam parando todas as tracks do stream.
        
        Usado quando o usuário sai da aba webcam ou clica em pausar.
        O stream é completamente encerrado para liberar a câmera.
        """
        if self.state.stream is not None:
            tracks = self.state.stream.getTracks()
            for i in range(tracks.length):
                tracks[i].stop()
            self.state.stream = None
            self.state.is_webcam_paused = True
            self.dom.video.classList.add('paused')
            self.dom.toggle_webcam_btn.innerHTML = "&#x25B6; Retomar Webcam"
            console.log("Webcam paused")
    
    async def resume(self):
        """
        Retoma a webcam após pausa.
        
        Reconecta à câmera previamente selecionada ou à primeira disponível.
        """
        if len(self.state.available_cameras) > 0:
            await self.switch_camera(
                self.dom.camera_select.value or self.state.available_cameras[0]["deviceId"]
            )
            self.state.is_webcam_paused = False
            self.dom.video.classList.remove('paused')
            self.dom.toggle_webcam_btn.innerHTML = "&#x23F8; Pausar Webcam"
            console.log("Webcam resumed")
    
    def toggle(self, event):
        """
        Alterna entre pausar e retomar a webcam.
        
        Args:
            event: Evento JavaScript do onClick
        """
        if self.state.stream is not None:
            self.pause()
        else:
            asyncio.ensure_future(self.resume())
    
    # --- Gravação ---
    
    def _on_data_available(self, event):
        """Callback quando dados de gravação estão disponíveis."""
        if event.data and event.data.size > 0:
            self.state.recorded_chunks.append(event.data)
    
    def start_recording(self):
        """Inicia gravação da webcam."""
        if self.state.stream is None:
            return
        
        self.state.recorded_chunks = []
        self.state.webcam_captions = []
        self.state.last_caption_time = None
        
        options = to_js({"mimeType": "video/webm;codecs=vp9"}, dict_converter=Object.fromEntries)
        
        try:
            self.state.media_recorder = window.MediaRecorder.new(self.state.stream, options)
        except:
            options = to_js({"mimeType": "video/webm"}, dict_converter=Object.fromEntries)
            self.state.media_recorder = window.MediaRecorder.new(self.state.stream, options)
        
        self.state.media_recorder.ondataavailable = create_proxy(self._on_data_available)
        self.state.media_recorder.start(1000)
        
        self.state.recording_start_time = window.performance.now() / 1000
        
        self.dom.recording_indicator.classList.remove('hidden')
        self.dom.video.classList.add('recording')
        self.dom.download_section.classList.add('hidden')
        
        console.log("Webcam recording started")
    
    def stop_recording(self):
        """Para gravação da webcam."""
        if self.state.media_recorder and self.state.media_recorder.state != "inactive":
            self.state.media_recorder.stop()
        
        self.state.recording_start_time = None
        
        self.dom.recording_indicator.classList.add('hidden')
        self.dom.video.classList.remove('recording')
        
        window.setTimeout(
            create_proxy(lambda: self.dom.download_section.classList.remove('hidden')), 
            500
        )
        
        console.log("Webcam recording stopped")
    
    def add_caption(self, text: str):
        """Adiciona legenda da webcam."""
        if self.state.recording_start_time is None:
            return
        
        current_time = window.performance.now() / 1000
        elapsed = current_time - self.state.recording_start_time
        
        start_time = self.state.last_caption_time if self.state.last_caption_time else elapsed
        end_time = elapsed
        
        if end_time > start_time and text and not text.startswith("Error"):
            self.state.webcam_captions.append({
                "start": start_time,
                "end": end_time,
                "text": text.strip()
            })
        
        self.state.last_caption_time = elapsed
    
    def download_video(self, event):
        """Download do vídeo da webcam."""
        if len(self.state.recorded_chunks) == 0:
            window.alert("Nenhum vídeo gravado!")
            return
        
        js_chunks = to_js(self.state.recorded_chunks)
        blob = Blob.new(js_chunks, to_js({"type": "video/webm"}, dict_converter=Object.fromEntries))
        
        url = URL.createObjectURL(blob)
        a = document.createElement('a')
        a.href = url
        a.download = "webcam_recording.webm"
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    
    def download_captions(self, event):
        """Download das legendas da webcam."""
        CaptionGenerator.download_srt(self.state.webcam_captions, "webcam_captions.srt")


# =============================================================================
# CLASSE: VideoPlayerManager
# =============================================================================
class VideoPlayerManager:
    """
    Gerencia player de vídeo local com controles completos.
    
    Esta classe implementa um player de vídeo personalizado com:
    - Upload de arquivos de vídeo locais
    - Controles: play, pause, stop, avançar, retroceder
    - Navegação frame a frame
    - Controle de velocidade de reprodução (0.25x a 2x)
    - Barra de progresso/timeline clicável
    - Modo loop/repetição
    - Captura de frames para análise
    - Geração de legendas sincronizadas
    
    Atributos:
        dom (DOMElements): Referência aos elementos do DOM
        state (AppState): Estado compartilhado da aplicação
    
    Controles disponíveis:
        - ▶️/⏸️ Play/Pause
        - ⏹️ Stop (volta ao início)
        - ⏮️/⏭️ Frame anterior/próximo
        - ⏪/⏩ Retroceder/avançar 5s
        - 🔁 Loop on/off
        - Slider de velocidade (0.25x-2x)
    """
    
    def __init__(self, dom: DOMElements, state: AppState):
        """
        Inicializa o gerenciador de player de vídeo.
        
        Args:
            dom: Instância de DOMElements
            state: Instância de AppState para estado compartilhado
        """
        self.dom = dom
        self.state = state
    
    def on_file_selected(self, event):
        """Callback quando arquivo de vídeo é selecionado via input file."""
        files = self.dom.video_file_input.files
        if files.length > 0:
            self.load_file(files.item(0))
    
    def load_file(self, file):
        """
        Carrega arquivo de vídeo no player.
        
        Cria uma URL de objeto temporária para o arquivo e associa
        ao elemento <video>. Reseta legendas anteriores.
        
        Args:
            file: Objeto File do JavaScript (FileAPI)
        """
        self.state.video_captions = []
        self.state.video_last_caption_time = None
        
        url = URL.createObjectURL(file)
        self.dom.local_video.src = url
        
        self.dom.video_drop_zone.classList.add('hidden')
        self.dom.video_player_container.classList.remove('hidden')
        self.dom.video_download_section.classList.add('hidden')
        
        console.log(f"Video loaded: {file.name}")
    
    def on_loaded_metadata(self, event):
        """Callback quando metadados do vídeo são carregados (duração, dimensões)."""
        self.dom.video_timeline.max = self.dom.local_video.duration
        self.dom.total_time_display.textContent = CaptionGenerator.format_time_display(
            self.dom.local_video.duration
        )
        self.dom.current_time_display.textContent = "00:00"
        console.log(f"Video duration: {self.dom.local_video.duration}s")
    
    def on_time_update(self, event):
        """Callback chamado continuamente durante reprodução para atualizar UI."""
        self.dom.video_timeline.value = self.dom.local_video.currentTime
        self.dom.current_time_display.textContent = CaptionGenerator.format_time_display(
            self.dom.local_video.currentTime
        )
    
    def on_timeline_change(self, event):
        """Callback quando usuário arrasta a timeline/slider."""
        self.dom.local_video.currentTime = float(self.dom.video_timeline.value)
    
    def toggle_play_pause(self, event):
        """Alterna entre play e pause do vídeo."""
        if self.dom.local_video.paused:
            self.dom.local_video.play()
            self.dom.play_pause_btn.textContent = "⏸️"
        else:
            self.dom.local_video.pause()
            self.dom.play_pause_btn.textContent = "▶️"
    
    def stop(self, event):
        """Para o vídeo e volta ao início (currentTime = 0)."""
        self.dom.local_video.pause()
        self.dom.local_video.currentTime = 0
        self.dom.play_pause_btn.textContent = "▶️"
    
    def prev_frame(self, event):
        """Retrocede 1 frame (~33ms para vídeo 30fps)."""
        self.dom.local_video.pause()
        self.dom.local_video.currentTime = max(0, self.dom.local_video.currentTime - 0.033)
        self.dom.play_pause_btn.textContent = "▶️"
    
    def next_frame(self, event):
        """Avança 1 frame (~33ms para vídeo 30fps)."""
        self.dom.local_video.pause()
        self.dom.local_video.currentTime = min(
            self.dom.local_video.duration, 
            self.dom.local_video.currentTime + 0.033
        )
        self.dom.play_pause_btn.textContent = "▶️"
    
    def rewind(self, event):
        """Retrocede 5 segundos mantendo limites."""
        self.dom.local_video.currentTime = max(0, self.dom.local_video.currentTime - 5)
    
    def forward(self, event):
        """Avança 5 segundos mantendo limites."""
        self.dom.local_video.currentTime = min(
            self.dom.local_video.duration, 
            self.dom.local_video.currentTime + 5
        )
    
    def change_speed(self, event):
        """Altera velocidade de reprodução (0.25x a 2x)."""
        self.dom.local_video.playbackRate = float(self.dom.playback_speed_select.value)
        console.log(f"Playback speed: {self.dom.playback_speed_select.value}x")
    
    def toggle_loop(self, event):
        """Alterna modo loop/repetição do vídeo."""
        self.state.is_loop_enabled = not self.state.is_loop_enabled
        self.dom.local_video.loop = self.state.is_loop_enabled
        
        if self.state.is_loop_enabled:
            self.dom.toggle_loop_btn.classList.add('loop-active')
            console.log("Loop enabled")
        else:
            self.dom.toggle_loop_btn.classList.remove('loop-active')
            console.log("Loop disabled")
    
    def on_ended(self, event):
        """Callback quando o vídeo termina de reproduzir."""
        self.dom.play_pause_btn.textContent = "▶️"
        if not self.state.is_loop_enabled:
            console.log("Video ended")
    
    def show_upload(self, event):
        """Volta para área de upload para selecionar outro vídeo."""
        self.dom.video_player_container.classList.add('hidden')
        self.dom.video_drop_zone.classList.remove('hidden')
        self.dom.video_download_section.classList.add('hidden')
    
    def capture_frame(self) -> str:
        """
        Captura frame atual do vídeo como base64.
        
        Returns:
            String "data:image/jpeg;base64,..." ou None se vídeo não carregado
        """
        if self.dom.local_video.videoWidth == 0:
            return None
        
        self.dom.local_video_canvas.width = self.dom.local_video.videoWidth
        self.dom.local_video_canvas.height = self.dom.local_video.videoHeight
        context = self.dom.local_video_canvas.getContext('2d')
        context.drawImage(
            self.dom.local_video, 0, 0, 
            self.dom.local_video_canvas.width, 
            self.dom.local_video_canvas.height
        )
        return self.dom.local_video_canvas.toDataURL('image/jpeg', 0.8)
    
    def add_caption(self, text: str):
        """
        Adiciona legenda sincronizada ao vídeo.
        
        Usa o currentTime do vídeo para timestamps precisos.
        
        Args:
            text: Texto da legenda (resposta da API)
        """
        current_time = self.dom.local_video.currentTime
        
        start_time = self.state.video_last_caption_time if self.state.video_last_caption_time else current_time
        end_time = current_time
        
        if end_time > start_time and text and not text.startswith("Error"):
            self.state.video_captions.append({
                "start": start_time,
                "end": end_time,
                "text": text.strip()
            })
        
        self.state.video_last_caption_time = current_time
    
    def download_captions(self, event):
        """Dispara download do arquivo SRT com legendas do vídeo."""
        CaptionGenerator.download_srt(self.state.video_captions, "video_captions.srt")


# =============================================================================
# CLASSE: ImageAnalyzer
# =============================================================================
class ImageAnalyzer:
    """
    Gerencia upload e análise de imagens estáticas.
    
    Esta classe permite carregar uma imagem do computador e
    realizar uma análise única com o modelo de visão.
    
    Diferente do modo webcam/vídeo que faz análises contínuas,
    o modo imagem faz apenas uma análise por clique no botão.
    
    Atributos:
        dom (DOMElements): Referência aos elementos do DOM
        state (AppState): Estado compartilhado
        api_client (APIClient): Cliente para requisições à API
    
    Fluxo de uso:
        1. Usuário carrega imagem (clique ou drag & drop)
        2. Imagem é exibida na tela
        3. Usuário clica "Analisar"
        4. Resposta é exibida no campo de response
    """
    
    def __init__(self, dom: DOMElements, state: AppState, api_client: APIClient):
        """
        Inicializa o analisador de imagens.
        
        Args:
            dom: Elementos do DOM
            state: Estado da aplicação
            api_client: Cliente de API para requisições
        """
        self.dom = dom
        self.state = state
        self.api_client = api_client
    
    def on_file_selected(self, event):
        """Callback quando arquivo de imagem é selecionado via input file."""
        files = self.dom.image_file_input.files
        if files.length > 0:
            self.load_file(files.item(0))
    
    def load_file(self, file):
        """
        Carrega arquivo de imagem usando FileReader.
        
        Converte a imagem para base64 para exibição e posterior
        envio à API de análise.
        
        Args:
            file: Objeto File do JavaScript (FileAPI)
        """
        reader = FileReader.new()
        
        def on_load(e):
            self.state.current_image_base64 = reader.result
            self.dom.loaded_image.src = self.state.current_image_base64
            
            self.dom.image_drop_zone.classList.add('hidden')
            self.dom.image_viewer_container.classList.remove('hidden')
            
            console.log(f"Image loaded: {file.name}")
        
        reader.onload = create_proxy(on_load)
        reader.readAsDataURL(file)
    
    def show_upload(self, event):
        """Volta para área de upload para selecionar outra imagem."""
        self.dom.image_viewer_container.classList.add('hidden')
        self.dom.image_drop_zone.classList.remove('hidden')
    
    async def analyze(self):
        """Analisa a imagem carregada."""
        if self.state.current_image_base64 is None:
            self.dom.response_text.value = "Nenhuma imagem carregada."
            return
        
        self.dom.response_text.value = "Analisando imagem..."
        
        instruction = self.dom.instruction_text.value
        response = await self.api_client.send_request(instruction, self.state.current_image_base64)
        self.dom.response_text.value = response
    
    def on_analyze_click(self, event):
        """Callback do botão de análise de imagem."""
        asyncio.ensure_future(self.analyze())


# =============================================================================
# CLASSE: TabManager
# =============================================================================
class TabManager:
    """
    Gerencia navegação entre abas da aplicação.
    
    Esta classe controla a lógica de troca de abas, incluindo:
    - Atualização visual dos botões e painéis
    - Pausa/retomada automática da webcam
    - Parada de processamento ao trocar de aba
    - Ajuste de controles conforme a aba ativa
    
    Abas disponíveis:
        - "webcam": Captura em tempo real da câmera
        - "video": Player de vídeo local
        - "image": Análise de imagem estática
    
    Atributos:
        dom (DOMElements): Referência aos elementos do DOM
        state (AppState): Estado compartilhado
        webcam (WebcamManager): Gerenciador da webcam
        on_stop_callback: Função para parar processamento
    
    Comportamento especial:
        - Webcam pausa automaticamente ao sair da aba "webcam"
        - Webcam retoma automaticamente ao voltar para aba "webcam"
        - Processamento para ao trocar de qualquer aba
    """
    
    def __init__(self, dom: DOMElements, state: AppState, webcam: WebcamManager):
        """
        Inicializa o gerenciador de abas.
        
        Args:
            dom: Elementos do DOM
            state: Estado da aplicação
            webcam: Gerenciador de webcam para pause/resume automático
        """
        self.dom = dom
        self.state = state
        self.webcam = webcam
        self.on_stop_callback = None
    
    def set_stop_callback(self, callback):
        """
        Define callback para parar processamento ao trocar de aba.
        
        Args:
            callback: Função sem argumentos a ser chamada
        """
        self.on_stop_callback = callback
    
    def switch(self, event):
        """
        Alterna para a aba clicada.
        
        Executa as seguintes ações:
        1. Para processamento se estiver ativo
        2. Pausa webcam se saindo da aba webcam
        3. Atualiza classes CSS dos botões e painéis
        4. Ajusta controles conforme a nova aba
        5. Retoma webcam se entrando na aba webcam
        
        Args:
            event: Evento de clique no botão da aba
        """
        old_tab = self.state.current_tab
        
        # Para processamento ao trocar de aba
        if self.state.is_processing and self.on_stop_callback:
            self.on_stop_callback()
        
        # Obtém a aba clicada
        clicked_btn = event.target
        tab_name = clicked_btn.getAttribute('data-tab')
        
        if tab_name == old_tab:
            return
        
        # Pausa webcam ao sair da aba webcam
        if old_tab == "webcam" and self.state.stream is not None:
            self.webcam.pause()
        
        self.state.current_tab = tab_name
        
        # Atualiza estado visual dos botões de aba
        tab_buttons = document.querySelectorAll('.tab-btn')
        for i in range(tab_buttons.length):
            btn = tab_buttons[i]
            if btn.getAttribute('data-tab') == tab_name:
                btn.classList.add('active')
            else:
                btn.classList.remove('active')
        
        # Mostra/oculta painéis de conteúdo
        panels = document.querySelectorAll('.tab-panel')
        for i in range(panels.length):
            panel = panels[i]
            if panel.id == f"tab-{tab_name}":
                panel.classList.remove('hidden')
                panel.classList.add('active')
            else:
                panel.classList.add('hidden')
                panel.classList.remove('active')
        
        # Ajusta botão Start conforme a aba
        if tab_name == "image":
            self.dom.start_button.textContent = "Analisar"
            self.dom.interval_select.disabled = True
        else:
            self.dom.start_button.textContent = "Start"
            self.dom.interval_select.disabled = False
        
        # Retoma webcam ao voltar para aba webcam
        if tab_name == "webcam" and self.state.stream is None:
            asyncio.ensure_future(self.webcam.resume())
        
        console.log(f"Switched to tab: {tab_name}")


# =============================================================================
# CLASSE: VisionApp (Principal)
# =============================================================================
class VisionApp:
    """
    Classe principal que orquestra toda a aplicação Vision AI.
    
    Esta é a classe "orquestradora" que:
    - Instancia todos os componentes (DOM, State, Managers)
    - Configura event listeners para toda a UI
    - Implementa o loop de processamento principal
    - Gerencia início/parada do processamento
    
    Padrão de design:
        Segue o padrão de composição, onde VisionApp "compõe"
        instâncias de outras classes e coordena suas interações.
    
    Atributos:
        dom (DOMElements): Referências aos elementos HTML
        state (AppState): Estado global da aplicação
        api_client (APIClient): Cliente para API de visão
        webcam (WebcamManager): Gerenciador de webcam
        video_player (VideoPlayerManager): Player de vídeo
        image_analyzer (ImageAnalyzer): Analisador de imagens
        tab_manager (TabManager): Gerenciador de abas
    
    Ciclo de vida:
        1. __init__: Instancia componentes e registra listeners
        2. init(): Inicializa webcam (async)
        3. handle_start/stop: Controla processamento
        4. _processing_loop: Loop principal de análise
        5. _cleanup: Libera recursos ao sair
    
    Exemplo de uso (no final do arquivo):
        app = VisionApp()
        asyncio.ensure_future(app.init())
    """
    
    def __init__(self):
        """
        Inicializa a aplicação instanciando todos os componentes.
        
        A ordem de inicialização é importante:
        1. DOM e State primeiro (dependências básicas)
        2. APIClient (depende apenas de DOM)
        3. WebcamManager (depende de DOM e State)
        4. VideoPlayerManager e ImageAnalyzer
        5. TabManager (depende de WebcamManager)
        6. Event listeners por último
        """
        # Inicializa componentes base
        self.dom = DOMElements()
        self.state = AppState()
        self.api_client = APIClient(self.dom)
        
        # Inicializa managers
        self.webcam = WebcamManager(self.dom, self.state)
        self.video_player = VideoPlayerManager(self.dom, self.state)
        self.image_analyzer = ImageAnalyzer(self.dom, self.state, self.api_client)
        self.tab_manager = TabManager(self.dom, self.state, self.webcam)
        
        # Configura callbacks entre componentes
        self.tab_manager.set_stop_callback(self.handle_stop)
        
        # Registra event listeners
        self._setup_event_listeners()
        self._setup_drag_drop()
    
    def _setup_drag_drop(self):
        """
        Configura drag & drop para áreas de upload.
        
        Cria handlers genéricos para dragover, dragleave e drop,
        aplicando-os às zonas de vídeo e imagem.
        """
        
        def setup_zone(drop_zone, file_handler):
            """Configura uma zona de drop específica."""
            def on_dragover(e):
                e.preventDefault()
                drop_zone.classList.add('dragover')
            
            def on_dragleave(e):
                drop_zone.classList.remove('dragover')
            
            def on_drop(e):
                e.preventDefault()
                drop_zone.classList.remove('dragover')
                files = e.dataTransfer.files
                if files.length > 0:
                    file_handler(files.item(0))
            
            drop_zone.addEventListener('dragover', create_proxy(on_dragover))
            drop_zone.addEventListener('dragleave', create_proxy(on_dragleave))
            drop_zone.addEventListener('drop', create_proxy(on_drop))
        
        # Aplica aos dois tipos de upload
        setup_zone(self.dom.video_drop_zone, self.video_player.load_file)
        setup_zone(self.dom.image_drop_zone, self.image_analyzer.load_file)
    
    def _setup_event_listeners(self):
        """
        Registra todos os event listeners da aplicação.
        
        Organizado por seção:
        - Abas: navegação entre webcam/vídeo/imagem
        - Controles comuns: API, Start/Stop
        - Webcam: seleção de câmera, downloads
        - Vídeo: controles do player
        - Imagem: upload e análise
        - Teclado: atalhos para player
        - Window: limpeza ao sair
        """
        
        # --- Abas ---
        tab_buttons = document.querySelectorAll('.tab-btn')
        for i in range(tab_buttons.length):
            tab_buttons[i].addEventListener('click', create_proxy(self.tab_manager.switch))
        
        # --- Controles Comuns ---
        self.dom.api_provider.addEventListener('change', create_proxy(self.api_client.update_base_url))
        self.dom.start_button.addEventListener('click', create_proxy(self.toggle_processing))
        
        # --- Webcam ---
        self.dom.camera_select.addEventListener('change', create_proxy(self.webcam.on_camera_change))
        self.dom.download_video_btn.addEventListener('click', create_proxy(self.webcam.download_video))
        self.dom.download_captions_btn.addEventListener('click', create_proxy(self.webcam.download_captions))
        self.dom.toggle_webcam_btn.addEventListener('click', create_proxy(self.webcam.toggle))
        
        # --- Vídeo Local ---
        self.dom.video_file_input.addEventListener('change', create_proxy(self.video_player.on_file_selected))
        self.dom.local_video.addEventListener('loadedmetadata', create_proxy(self.video_player.on_loaded_metadata))
        self.dom.local_video.addEventListener('timeupdate', create_proxy(self.video_player.on_time_update))
        self.dom.video_timeline.addEventListener('input', create_proxy(self.video_player.on_timeline_change))
        self.dom.play_pause_btn.addEventListener('click', create_proxy(self.video_player.toggle_play_pause))
        self.dom.stop_video_btn.addEventListener('click', create_proxy(self.video_player.stop))
        self.dom.prev_frame_btn.addEventListener('click', create_proxy(self.video_player.prev_frame))
        self.dom.next_frame_btn.addEventListener('click', create_proxy(self.video_player.next_frame))
        self.dom.rewind_btn.addEventListener('click', create_proxy(self.video_player.rewind))
        self.dom.forward_btn.addEventListener('click', create_proxy(self.video_player.forward))
        self.dom.playback_speed_select.addEventListener('change', create_proxy(self.video_player.change_speed))
        self.dom.change_video_btn.addEventListener('click', create_proxy(self.video_player.show_upload))
        self.dom.download_video_srt_btn.addEventListener('click', create_proxy(self.video_player.download_captions))
        self.dom.toggle_loop_btn.addEventListener('click', create_proxy(self.video_player.toggle_loop))
        self.dom.local_video.addEventListener('ended', create_proxy(self.video_player.on_ended))
        
        # --- Imagem ---
        self.dom.image_file_input.addEventListener('change', create_proxy(self.image_analyzer.on_file_selected))
        self.dom.analyze_image_btn.addEventListener('click', create_proxy(self.image_analyzer.on_analyze_click))
        self.dom.change_image_btn.addEventListener('click', create_proxy(self.image_analyzer.show_upload))
        
        # --- Atalhos de Teclado ---
        document.addEventListener('keydown', create_proxy(self._on_keydown))
        
        # --- Limpeza ao Sair ---
        window.addEventListener('beforeunload', create_proxy(self._cleanup))
    
    def _on_keydown(self, event):
        """
        Trata atalhos de teclado globais.
        
        Atalhos disponíveis (apenas na aba vídeo):
        - Espaço: Play/Pause
        - Seta Esquerda: Frame anterior
        - Seta Direita: Próximo frame
        
        Args:
            event: Evento de teclado
        """
        # Ignora se estiver digitando em campos de texto
        tag = event.target.tagName.lower()
        if tag in ['input', 'textarea', 'select']:
            return
        
        key = event.key
        
        # Atalhos apenas na aba de vídeo
        if self.state.current_tab == "video":
            if key == " ":  # Espaço = Play/Pause
                event.preventDefault()
                self.video_player.toggle_play_pause(event)
            elif key == "ArrowLeft":  # Seta esquerda = Frame anterior
                event.preventDefault()
                self.video_player.prev_frame(event)
            elif key == "ArrowRight":  # Seta direita = Próximo frame
                event.preventDefault()
                self.video_player.next_frame(event)
    
    def _cleanup(self, event):
        """
        Libera recursos ao sair da página.
        
        Para processamento e libera tracks da webcam para
        desligar o indicador de câmera ativa no navegador.
        """
        self.state.is_processing = False
        
        if self.state.stream:
            tracks = self.state.stream.getTracks()
            for i in range(tracks.length):
                tracks[i].stop()
    
    # --- Processamento ---
    
    async def _send_data(self):
        """Processa frame conforme a aba atual."""
        if not self.state.is_processing:
            return
        
        instruction = self.dom.instruction_text.value
        image_base64 = None
        
        if self.state.current_tab == "webcam":
            image_base64 = self.webcam.capture_frame()
        elif self.state.current_tab == "video":
            image_base64 = self.video_player.capture_frame()
        
        if image_base64 is None:
            self.dom.response_text.value = "Falha ao capturar frame."
            return
        
        response = await self.api_client.send_request(instruction, image_base64)
        self.dom.response_text.value = response
        
        # Adiciona legenda
        if self.state.current_tab == "webcam":
            if self.dom.enable_recording.checked and self.state.recording_start_time is not None:
                self.webcam.add_caption(response)
        elif self.state.current_tab == "video":
            self.video_player.add_caption(response)
    
    async def _processing_loop(self):
        """Loop principal de processamento."""
        interval_ms = int(self.dom.interval_select.value)
        interval_s = interval_ms / 1000.0
        
        while self.state.is_processing:
            await self._send_data()
            await asyncio.sleep(interval_s)
    
    def handle_start(self):
        """Inicia o processamento."""
        # Validações
        url_value = self.dom.base_url.value
        if not (url_value.startswith('http://') or url_value.startswith('https://')):
            self.dom.response_text.value = "URL inválida. Use http:// ou https://"
            return
        
        if self.state.current_tab == "webcam":
            if self.state.stream is None:
                self.dom.response_text.value = "Câmera não disponível."
                return
        elif self.state.current_tab == "video":
            if self.dom.local_video.src == "":
                self.dom.response_text.value = "Nenhum vídeo carregado."
                return
            # Reseta legendas do vídeo
            self.state.video_captions = []
            self.state.video_last_caption_time = None
            # Inicia o vídeo
            self.dom.local_video.play()
            self.dom.play_pause_btn.textContent = "⏸️"
        elif self.state.current_tab == "image":
            # Para imagem, faz análise única
            asyncio.ensure_future(self.image_analyzer.analyze())
            return
        
        self.state.is_processing = True
        self.dom.start_button.textContent = "Stop"
        self.dom.start_button.classList.remove('start')
        self.dom.start_button.classList.add('stop')
        
        # Desabilita controles
        self.dom.instruction_text.disabled = True
        self.dom.interval_select.disabled = True
        self.dom.api_provider.disabled = True
        self.dom.base_url.disabled = True
        
        if self.state.current_tab == "webcam":
            self.dom.enable_recording.disabled = True
            if self.dom.enable_recording.checked:
                self.webcam.start_recording()
        
        self.dom.response_text.value = "Processando..."
        
        self.state.processing_task = asyncio.ensure_future(self._processing_loop())
    
    def handle_stop(self):
        """Para o processamento."""
        self.state.is_processing = False
        
        if self.state.processing_task:
            self.state.processing_task.cancel()
            self.state.processing_task = None
        
        self.dom.start_button.textContent = "Start" if self.state.current_tab != "image" else "Analisar"
        self.dom.start_button.classList.remove('stop')
        self.dom.start_button.classList.add('start')
        
        # Reabilita controles
        self.dom.instruction_text.disabled = False
        self.dom.interval_select.disabled = self.state.current_tab == "image"
        self.dom.api_provider.disabled = False
        self.dom.base_url.disabled = False
        
        if self.state.current_tab == "webcam":
            self.dom.enable_recording.disabled = False
            if self.dom.enable_recording.checked:
                self.webcam.stop_recording()
        elif self.state.current_tab == "video":
            self.dom.local_video.pause()
            self.dom.play_pause_btn.textContent = "▶️"
            # Mostra download de legendas
            if len(self.state.video_captions) > 0:
                self.dom.video_download_section.classList.remove('hidden')
        
        if self.dom.response_text.value == "Processando...":
            self.dom.response_text.value = "Processamento parado."
    
    def toggle_processing(self, event):
        """Alterna entre iniciar e parar."""
        if self.state.is_processing:
            self.handle_stop()
        else:
            self.handle_start()
    
    async def init(self):
        """Inicializa a aplicação."""
        await self.webcam.init()
        self.dom.loading_overlay.classList.add('hidden')
        console.log("Vision AI App initialized!")


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

# Cria e inicializa a aplicação
app = VisionApp()
asyncio.ensure_future(app.init())
