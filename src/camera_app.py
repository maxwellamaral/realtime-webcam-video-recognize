"""
Camera Interaction App - PyScript Version
==========================================
Aplicação de interação com câmera usando Python no navegador.
Com suporte a gravação de vídeo e legendas timestampadas.

Este módulo utiliza PyScript para executar Python diretamente no navegador,
fazendo ponte com APIs JavaScript como MediaRecorder e fetch.

Funcionalidades:
- Captura de vídeo da webcam
- Envio de frames para API de visão computacional (LM Studio / llama.cpp)
- Gravação opcional do vídeo com legendas em formato SRT
"""

# =============================================================================
# IMPORTS
# =============================================================================
# Módulos JavaScript acessíveis via PyScript
from js import document, navigator, console, JSON, Object, window, fetch, Blob, URL, Array
# Utilitários para interoperabilidade Python <-> JavaScript
from pyodide.ffi import create_proxy, to_js
# Suporte a operações assíncronas
import asyncio
# Parsing de respostas JSON da API
import json

# =============================================================================
# ELEMENTOS DO DOM
# =============================================================================
# Referências aos elementos HTML que serão manipulados pelo Python

# Elementos de vídeo
video = document.getElementById('videoFeed')          # Elemento <video> que exibe a webcam
canvas = document.getElementById('canvas')            # Canvas oculto para capturar frames

# Elementos de configuração da API
api_provider = document.getElementById('apiProvider')         # Select do provedor (LM Studio / llama.cpp)
base_url = document.getElementById('baseURL')                 # Input da URL base da API
instruction_text = document.getElementById('instructionText') # Textarea com instrução para o modelo
response_text = document.getElementById('responseText')       # Textarea para exibir respostas

# Elementos de controle
interval_select = document.getElementById('intervalSelect')   # Select do intervalo entre requisições
start_button = document.getElementById('startButton')         # Botão Start/Stop
loading_overlay = document.getElementById('loadingOverlay')   # Overlay de carregamento do PyScript

# Elementos de gravação
enable_recording = document.getElementById('enableRecording')     # Checkbox para ativar gravação
recording_indicator = document.getElementById('recordingIndicator') # Indicador "● REC"
download_section = document.getElementById('downloadSection')     # Seção com botões de download
download_video_btn = document.getElementById('downloadVideo')     # Botão download vídeo
download_captions_btn = document.getElementById('downloadCaptions') # Botão download legendas

# Elemento de seleção de câmera
camera_select = document.getElementById('cameraSelect')          # Select para escolher câmera

# =============================================================================
# ESTADO GLOBAL DA APLICAÇÃO
# =============================================================================

# Estado do stream de vídeo
stream = None           # MediaStream da webcam (None se câmera não ativa)
is_processing = False   # Flag indicando se o loop de processamento está ativo
processing_task = None  # Referência à Task do asyncio para o loop

# Estado da gravação
media_recorder = None       # Instância do MediaRecorder para gravar vídeo
recorded_chunks = []        # Lista de Blobs com chunks do vídeo gravado
captions = []               # Lista de legendas: [{start, end, text}, ...]
recording_start_time = None # Timestamp (segundos) do início da gravação
last_caption_time = None    # Timestamp da última legenda (para calcular duração)

# Lista de câmeras disponíveis
available_cameras = []      # Lista de dispositivos de vídeo {deviceId, label}


# =============================================================================
# FUNÇÕES DE CONFIGURAÇÃO
# =============================================================================

def update_base_url(event):
    """
    Atualiza a URL base automaticamente quando o provedor de API muda.
    
    Cada provedor usa uma porta padrão diferente:
    - llama.cpp: porta 8080
    - LM Studio: porta 1234
    """
    provider = api_provider.value
    if provider == 'llamacpp':
        base_url.value = 'http://localhost:8080'
    elif provider == 'lmstudio':
        base_url.value = 'http://localhost:1234'


# =============================================================================
# FUNÇÕES DE COMUNICAÇÃO COM A API
# =============================================================================

async def send_chat_completion_request(instruction: str, image_base64_url: str) -> str:
    """
    Envia uma requisição para a API de chat completion com imagem.
    
    Args:
        instruction: Texto de instrução para o modelo (ex: "What do you see?")
        image_base64_url: Imagem codificada em base64 como data URL
        
    Returns:
        String com a resposta do modelo ou mensagem de erro
        
    A requisição segue o formato OpenAI Chat Completions API com suporte a visão.
    """
    try:
        url = f"{base_url.value}/v1/chat/completions"
        
        # Payload no formato OpenAI Chat Completions com conteúdo multimodal
        payload = {
            "max_tokens": 100,  # Limita tamanho da resposta para respostas rápidas
            "messages": [
                {
                    "role": "user",
                    "content": [
                        # Texto da instrução
                        {"type": "text", "text": instruction},
                        # Imagem em base64
                        {"type": "image_url", "image_url": {"url": image_base64_url}}
                    ]
                }
            ]
        }
        
        # Converte objetos Python para JavaScript (necessário para fetch)
        js_payload = to_js(payload, dict_converter=Object.fromEntries)
        headers = to_js({"Content-Type": "application/json"}, dict_converter=Object.fromEntries)
        
        options = to_js({
            "method": "POST",
            "headers": headers,
            "body": JSON.stringify(js_payload)
        }, dict_converter=Object.fromEntries)
        
        # Faz a requisição HTTP
        response = await fetch(url, options)
        
        # Tratamento de erros HTTP
        if not response.ok:
            status = response.status
            error_msg = f"Server error: {status}"
            
            # Mensagens de erro amigáveis para problemas comuns
            if status == 404:
                error_msg += " - Endpoint not found. Make sure the server is running."
            elif status == 500:
                error_msg += " - Server error. Check if the model supports vision."
            elif status in [400, 422]:
                error_msg += " - Invalid request format."
            
            return error_msg
        
        # Parse da resposta JSON
        data_text = await response.text()
        data = json.loads(data_text)
        
        # Validação da estrutura da resposta
        if 'choices' not in data or len(data['choices']) == 0:
            return "Error: Invalid response format from server"
        
        if 'message' not in data['choices'][0]:
            return "Error: Invalid response format from server"
        
        # Retorna o conteúdo da resposta
        return data['choices'][0]['message']['content']
        
    except Exception as e:
        console.log(f"Error in request: {str(e)}")
        return f"Error: {str(e)}"


# =============================================================================
# FUNÇÕES DE CÂMERA
# =============================================================================

async def enumerate_cameras():
    """
    Enumera todas as câmeras disponíveis no dispositivo.
    
    Usa a API MediaDevices.enumerateDevices() para listar
    todos os dispositivos de vídeo e popula o dropdown de seleção.
    """
    global available_cameras
    
    console.log("Starting camera enumeration...")
    
    try:
        # Limpa o dropdown primeiro (remove todas as opções)
        while camera_select.options.length > 0:
            camera_select.remove(0)
        
        # Primeiro, solicita permissão de câmera para obter labels
        # (sem permissão, os labels vêm vazios)
        console.log("Requesting camera permission...")
        temp_constraints = to_js({"video": True, "audio": False}, dict_converter=Object.fromEntries)
        temp_stream = await navigator.mediaDevices.getUserMedia(temp_constraints)
        
        console.log("Permission granted, stopping temp stream...")
        
        # Para o stream temporário
        tracks = temp_stream.getTracks()
        for i in range(tracks.length):
            tracks[i].stop()
        
        # Agora enumera os dispositivos (com labels)
        console.log("Enumerating devices...")
        devices = await navigator.mediaDevices.enumerateDevices()
        
        console.log(f"Total devices found: {devices.length}")
        
        # Filtra apenas dispositivos de vídeo (câmeras)
        available_cameras = []
        
        for i in range(devices.length):
            device = devices[i]
            console.log(f"Device {i}: kind={device.kind}, label={device.label}")
            
            if device.kind == "videoinput":
                device_id = device.deviceId
                # Usa label ou nome genérico se não disponível
                label = device.label if device.label else f"Câmera {len(available_cameras) + 1}"
                
                available_cameras.append({
                    "deviceId": device_id,
                    "label": label
                })
                
                # Adiciona opção ao dropdown
                option = document.createElement("option")
                option.value = device_id
                option.textContent = label
                camera_select.appendChild(option)
                console.log(f"Added camera: {label}")
        
        console.log(f"Found {len(available_cameras)} camera(s)")
        
        if len(available_cameras) == 0:
            option = document.createElement("option")
            option.value = ""
            option.textContent = "Nenhuma câmera encontrada"
            camera_select.appendChild(option)
            
    except Exception as e:
        console.error(f"Error enumerating cameras: {str(e)}")
        # Limpa o dropdown em caso de erro
        while camera_select.options.length > 0:
            camera_select.remove(0)
        option = document.createElement("option")
        option.value = ""
        option.textContent = f"Erro: {str(e)}"
        camera_select.appendChild(option)


async def switch_camera(device_id: str = None):
    """
    Troca para uma câmera específica.
    
    Args:
        device_id: ID do dispositivo de câmera (ou None para usar padrão)
        
    Para o stream atual e inicia um novo com a câmera selecionada.
    """
    global stream
    
    try:
        # Para o stream atual se existir
        if stream:
            tracks = stream.getTracks()
            for i in range(tracks.length):
                tracks[i].stop()
        
        # Configura constraints com deviceId específico se fornecido
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
        
        # Solicita acesso à câmera selecionada
        stream = await navigator.mediaDevices.getUserMedia(constraints)
        
        # Conecta o stream ao elemento de vídeo
        video.srcObject = stream
        
        response_text.value = "Câmera alterada com sucesso."
        console.log(f"Switched to camera: {device_id}")
        
    except Exception as e:
        error_msg = f"Erro ao trocar câmera: {str(e)}"
        console.error(error_msg)
        response_text.value = error_msg


def on_camera_change(event):
    """
    Callback quando o usuário seleciona outra câmera no dropdown.
    """
    device_id = camera_select.value
    if device_id:
        asyncio.ensure_future(switch_camera(device_id))


async def init_camera():
    """
    Inicializa o acesso à webcam do usuário.
    
    Enumera câmeras disponíveis, popula o dropdown de seleção,
    e conecta a primeira câmera ao elemento <video>.
    Requer HTTPS ou localhost por questões de segurança do navegador.
    """
    global stream
    
    try:
        # Enumera câmeras disponíveis primeiro
        await enumerate_cameras()
        
        # Se houver câmeras, conecta a primeira
        if len(available_cameras) > 0:
            first_camera_id = available_cameras[0]["deviceId"]
            await switch_camera(first_camera_id)
            response_text.value = "Câmera inicializada. Pronto para começar."
        else:
            response_text.value = "Nenhuma câmera encontrada."
        
        console.log("Camera initialized successfully")
        
    except Exception as e:
        error_msg = f"Error accessing camera: {str(e)}"
        console.error(error_msg)
        response_text.value = error_msg
        window.alert("Error accessing camera. Make sure you've granted permission.")


def capture_image() -> str:
    """
    Captura o frame atual do vídeo como imagem base64.
    
    Returns:
        String com data URL da imagem (formato: data:image/jpeg;base64,...)
        ou None se o stream não estiver pronto
        
    Usa um canvas oculto para desenhar o frame e extrair como JPEG.
    """
    global stream
    
    # Verifica se o stream está ativo e tem dimensões válidas
    if stream is None or video.videoWidth == 0:
        console.warn("Video stream not ready for capture.")
        return None
    
    # Configura o canvas com as dimensões do vídeo
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    
    # Desenha o frame atual do vídeo no canvas
    context = canvas.getContext('2d')
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    
    # Converte para JPEG base64 (qualidade 0.8 para balancear tamanho/qualidade)
    return canvas.toDataURL('image/jpeg', 0.8)


# =============================================================================
# FUNÇÕES DE LEGENDAS (SRT)
# =============================================================================

def format_time_srt(seconds: float) -> str:
    """
    Formata tempo em segundos para o formato SRT.
    
    Args:
        seconds: Tempo em segundos (ex: 65.5)
        
    Returns:
        String no formato HH:MM:SS,mmm (ex: "00:01:05,500")
        
    Nota: SRT usa VÍRGULA para milissegundos (diferente de VTT que usa ponto)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def add_caption(text: str):
    """
    Adiciona uma nova legenda com timestamps calculados.
    
    Args:
        text: Texto da legenda (resposta da API)
        
    O timestamp de início é o fim da legenda anterior (ou tempo atual se primeira).
    O timestamp de fim é o tempo atual.
    Legendas com erro são ignoradas.
    """
    global captions, recording_start_time, last_caption_time
    
    # Ignora se não estiver gravando
    if recording_start_time is None:
        return
    
    # Calcula tempo decorrido desde o início da gravação
    current_time = window.performance.now() / 1000  # Converte ms para segundos
    elapsed = current_time - recording_start_time
    
    # Define timestamps da legenda
    start_time = last_caption_time if last_caption_time else elapsed
    end_time = elapsed
    
    # Adiciona apenas se tiver duração válida e não for erro
    if end_time > start_time and text and not text.startswith("Error"):
        captions.append({
            "start": start_time,
            "end": end_time,
            "text": text.strip()
        })
    
    # Atualiza o tempo da última legenda
    last_caption_time = elapsed


def generate_srt_content() -> str:
    """
    Gera o conteúdo completo do arquivo SRT.
    
    Returns:
        String formatada no padrão SRT pronta para salvar em arquivo
        
    Formato SRT:
        1
        00:00:00,500 --> 00:00:02,500
        Texto da primeira legenda
        
        2
        00:00:02,500 --> 00:00:04,500
        Texto da segunda legenda
    """
    srt_lines = []
    
    for i, caption in enumerate(captions, 1):
        start = format_time_srt(caption["start"])
        end = format_time_srt(caption["end"])
        text = caption["text"]
        
        # Número sequencial da legenda
        srt_lines.append(f"{i}")
        # Timestamps de início e fim
        srt_lines.append(f"{start} --> {end}")
        # Texto da legenda
        srt_lines.append(text)
        # Linha em branco separadora
        srt_lines.append("")
    
    return "\n".join(srt_lines)


# =============================================================================
# FUNÇÕES DE GRAVAÇÃO DE VÍDEO
# =============================================================================

def on_data_available(event):
    """
    Callback chamado quando novos dados de vídeo estão disponíveis.
    
    O MediaRecorder chama esta função periodicamente (a cada 1 segundo)
    com chunks de dados do vídeo sendo gravado.
    """
    global recorded_chunks
    if event.data and event.data.size > 0:
        recorded_chunks.append(event.data)


def start_recording():
    """
    Inicia a gravação de vídeo usando a API MediaRecorder.
    
    Configura o MediaRecorder para gravar o stream da webcam
    no formato WebM com codec VP9 (ou fallback para WebM padrão).
    """
    global media_recorder, recorded_chunks, captions, recording_start_time, last_caption_time
    
    if stream is None:
        return
    
    # Reseta estado da gravação anterior
    recorded_chunks = []
    captions = []
    last_caption_time = None
    
    # Tenta criar MediaRecorder com VP9 (melhor qualidade)
    options = to_js({"mimeType": "video/webm;codecs=vp9"}, dict_converter=Object.fromEntries)
    
    try:
        media_recorder = window.MediaRecorder.new(stream, options)
    except:
        # Fallback para codec padrão se VP9 não suportado
        options = to_js({"mimeType": "video/webm"}, dict_converter=Object.fromEntries)
        media_recorder = window.MediaRecorder.new(stream, options)
    
    # Configura callback para receber dados
    media_recorder.ondataavailable = create_proxy(on_data_available)
    
    # Inicia gravação, coletando dados a cada 1000ms
    media_recorder.start(1000)
    
    # Marca o timestamp de início para cálculo das legendas
    recording_start_time = window.performance.now() / 1000
    
    # Atualiza UI para indicar gravação
    recording_indicator.classList.remove('hidden')  # Mostra "● REC"
    video.classList.add('recording')                 # Adiciona borda vermelha
    download_section.classList.add('hidden')         # Esconde downloads anteriores
    
    console.log("Recording started")


def stop_recording():
    """
    Para a gravação de vídeo e prepara os downloads.
    
    Finaliza o MediaRecorder e após um breve delay
    exibe os botões de download para o usuário.
    """
    global media_recorder, recording_start_time
    
    # Para o MediaRecorder se estiver ativo
    if media_recorder and media_recorder.state != "inactive":
        media_recorder.stop()
    
    recording_start_time = None
    
    # Atualiza UI
    recording_indicator.classList.add('hidden')   # Esconde "● REC"
    video.classList.remove('recording')           # Remove borda vermelha
    
    # Mostra seção de downloads após delay (garante dados prontos)
    window.setTimeout(create_proxy(lambda: download_section.classList.remove('hidden')), 500)
    
    console.log("Recording stopped")


# =============================================================================
# FUNÇÕES DE DOWNLOAD
# =============================================================================

def download_video(event):
    """
    Faz download do vídeo gravado como arquivo .webm
    
    Combina todos os chunks gravados em um único Blob
    e dispara o download usando um link temporário.
    """
    global recorded_chunks
    
    if len(recorded_chunks) == 0:
        window.alert("Nenhum vídeo gravado!")
        return
    
    # Combina todos os chunks em um único Blob
    js_chunks = to_js(recorded_chunks)
    blob = Blob.new(js_chunks, to_js({"type": "video/webm"}, dict_converter=Object.fromEntries))
    
    # Cria URL temporária para o Blob
    url = URL.createObjectURL(blob)
    
    # Cria e clica em um link para disparar o download
    a = document.createElement('a')
    a.href = url
    a.download = "recording.webm"
    document.body.appendChild(a)
    a.click()
    
    # Limpa o link e a URL temporária
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    console.log("Video downloaded")


def download_captions_file(event):
    """
    Faz download das legendas em formato SRT.
    
    Gera o conteúdo SRT a partir das legendas capturadas
    e dispara o download como arquivo de texto.
    """
    global captions
    
    if len(captions) == 0:
        window.alert("Nenhuma legenda gerada!")
        return
    
    # Gera conteúdo do arquivo SRT
    srt_content = generate_srt_content()
    
    # Cria Blob com o conteúdo texto
    blob = Blob.new(
        to_js([srt_content]),
        to_js({"type": "text/plain"}, dict_converter=Object.fromEntries)
    )
    
    # Dispara download
    url = URL.createObjectURL(blob)
    a = document.createElement('a')
    a.href = url
    a.download = "captions.srt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    console.log("Captions downloaded")


# =============================================================================
# LOOP PRINCIPAL DE PROCESSAMENTO
# =============================================================================

async def send_data():
    """
    Captura um frame e envia para a API de visão.
    
    Esta função é chamada repetidamente pelo processing_loop
    no intervalo configurado pelo usuário.
    """
    global is_processing
    
    if not is_processing:
        return
    
    # Obtém a instrução do usuário
    instruction = instruction_text.value
    
    # Captura o frame atual da webcam
    image_base64_url = capture_image()
    
    if image_base64_url is None:
        response_text.value = "Failed to capture image. Stream might not be active."
        return
    
    # Envia para a API e obtém resposta
    response = await send_chat_completion_request(instruction, image_base64_url)
    
    # Exibe resposta na interface
    response_text.value = response
    
    # Se gravação ativada, adiciona a resposta como legenda
    if enable_recording.checked and recording_start_time is not None:
        add_caption(response)


async def processing_loop():
    """
    Loop principal que processa frames continuamente.
    
    Executa send_data() no intervalo configurado pelo usuário
    até que is_processing seja definido como False.
    """
    global is_processing
    
    # Obtém intervalo configurado (em ms) e converte para segundos
    interval_ms = int(interval_select.value)
    interval_s = interval_ms / 1000.0
    
    while is_processing:
        await send_data()
        await asyncio.sleep(interval_s)


# =============================================================================
# CONTROLES DE INÍCIO/PARADA
# =============================================================================

def handle_start():
    """
    Inicia o processamento de vídeo.
    
    Valida configurações, inicia o loop de processamento
    e opcionalmente inicia a gravação de vídeo.
    """
    global is_processing, stream, processing_task
    
    # Verifica se a câmera está disponível
    if stream is None:
        response_text.value = "Camera not available. Cannot start."
        window.alert("Camera not available. Please grant permission first.")
        return
    
    # Valida formato da URL base
    url_value = base_url.value
    if not (url_value.startswith('http://') or url_value.startswith('https://')):
        response_text.value = "Invalid base URL. Must start with http:// or https://"
        window.alert("Please enter a valid base URL (e.g., http://localhost:1234)")
        return
    
    # Atualiza estado
    is_processing = True
    
    # Atualiza botão para modo "Stop"
    start_button.textContent = "Stop"
    start_button.classList.remove('start')
    start_button.classList.add('stop')
    
    # Desabilita controles durante processamento
    instruction_text.disabled = True
    interval_select.disabled = True
    api_provider.disabled = True
    base_url.disabled = True
    enable_recording.disabled = True
    
    response_text.value = "Processing started..."
    
    # Inicia gravação se checkbox marcado
    if enable_recording.checked:
        start_recording()
    
    # Inicia o loop de processamento assíncrono
    processing_task = asyncio.ensure_future(processing_loop())


def handle_stop():
    """
    Para o processamento de vídeo.
    
    Cancela o loop, para a gravação se ativa,
    e reabilita os controles da interface.
    """
    global is_processing, processing_task
    
    is_processing = False
    
    # Cancela a task do loop
    if processing_task:
        processing_task.cancel()
        processing_task = None
    
    # Para a gravação se estava ativa
    if enable_recording.checked:
        stop_recording()
    
    # Atualiza botão para modo "Start"
    start_button.textContent = "Start"
    start_button.classList.remove('stop')
    start_button.classList.add('start')
    
    # Reabilita controles
    instruction_text.disabled = False
    interval_select.disabled = False
    api_provider.disabled = False
    base_url.disabled = False
    enable_recording.disabled = False
    
    if response_text.value.startswith("Processing started..."):
        response_text.value = "Processing stopped."


def toggle_processing(event):
    """
    Alterna entre iniciar e parar o processamento.
    Callback do botão Start/Stop.
    """
    global is_processing
    if is_processing:
        handle_stop()
    else:
        handle_start()


# =============================================================================
# LIMPEZA DE RECURSOS
# =============================================================================

def cleanup(event):
    """
    Limpa recursos ao sair da página.
    
    Para o processamento e libera a câmera para que
    outros aplicativos possam utilizá-la.
    """
    global stream, is_processing
    
    is_processing = False
    
    if stream:
        # Para todas as tracks do stream (libera a câmera)
        tracks = stream.getTracks()
        for i in range(tracks.length):
            tracks[i].stop()


# =============================================================================
# REGISTRO DE EVENT LISTENERS
# =============================================================================

# Conecta eventos da interface às funções Python
api_provider.addEventListener('change', create_proxy(update_base_url))
start_button.addEventListener('click', create_proxy(toggle_processing))
download_video_btn.addEventListener('click', create_proxy(download_video))
download_captions_btn.addEventListener('click', create_proxy(download_captions_file))
camera_select.addEventListener('change', create_proxy(on_camera_change))

# Limpa recursos quando o usuário fecha/navega para fora da página
window.addEventListener('beforeunload', create_proxy(cleanup))


# =============================================================================
# INICIALIZAÇÃO DA APLICAÇÃO
# =============================================================================

async def main():
    """
    Função principal de inicialização.
    
    Inicializa a câmera e remove o overlay de carregamento
    quando o PyScript estiver pronto.
    """
    await init_camera()
    loading_overlay.classList.add('hidden')
    console.log("PyScript Camera App initialized!")


# Inicia a aplicação assim que o módulo é carregado
asyncio.ensure_future(main())
