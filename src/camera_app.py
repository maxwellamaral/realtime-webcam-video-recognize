"""
Vision AI - PyScript Application
=================================
Aplicação de análise de vídeo e imagem usando modelos de visão computacional.
Suporta webcam em tempo real, vídeos locais e imagens estáticas.

Este módulo utiliza PyScript para executar Python diretamente no navegador,
fazendo ponte com APIs JavaScript como MediaRecorder, File API e fetch.

Funcionalidades:
- Captura de vídeo da webcam com gravação e legendas
- Processamento de vídeos locais com player completo
- Análise de imagens estáticas
"""

# =============================================================================
# IMPORTS
# =============================================================================
from js import document, navigator, console, JSON, Object, window, fetch, Blob, URL, Array, FileReader
from pyodide.ffi import create_proxy, to_js
import asyncio
import json

# =============================================================================
# ELEMENTOS DO DOM - COMUM
# =============================================================================
api_provider = document.getElementById('apiProvider')
base_url = document.getElementById('baseURL')
instruction_text = document.getElementById('instructionText')
response_text = document.getElementById('responseText')
interval_select = document.getElementById('intervalSelect')
start_button = document.getElementById('startButton')
loading_overlay = document.getElementById('loadingOverlay')

# =============================================================================
# ELEMENTOS DO DOM - WEBCAM
# =============================================================================
video = document.getElementById('videoFeed')
canvas = document.getElementById('canvas')
camera_select = document.getElementById('cameraSelect')
enable_recording = document.getElementById('enableRecording')
recording_indicator = document.getElementById('recordingIndicator')
download_section = document.getElementById('downloadSection')
download_video_btn = document.getElementById('downloadVideo')
download_captions_btn = document.getElementById('downloadCaptions')
toggle_webcam_btn = document.getElementById('toggleWebcam')

# =============================================================================
# ELEMENTOS DO DOM - VÍDEO LOCAL
# =============================================================================
video_file_input = document.getElementById('videoFileInput')
video_drop_zone = document.getElementById('videoDropZone')
video_player_container = document.getElementById('videoPlayerContainer')
local_video = document.getElementById('localVideo')
local_video_canvas = document.getElementById('localVideoCanvas')
video_timeline = document.getElementById('videoTimeline')
current_time_display = document.getElementById('currentTime')
total_time_display = document.getElementById('totalTime')
play_pause_btn = document.getElementById('playPause')
stop_video_btn = document.getElementById('stopVideo')
prev_frame_btn = document.getElementById('prevFrame')
next_frame_btn = document.getElementById('nextFrame')
rewind_btn = document.getElementById('rewind')
forward_btn = document.getElementById('forward')
playback_speed_select = document.getElementById('playbackSpeed')
change_video_btn = document.getElementById('changeVideo')
video_download_section = document.getElementById('videoDownloadSection')
download_video_srt_btn = document.getElementById('downloadVideoSrt')
toggle_loop_btn = document.getElementById('toggleLoop')

# =============================================================================
# ELEMENTOS DO DOM - IMAGEM
# =============================================================================
image_file_input = document.getElementById('imageFileInput')
image_drop_zone = document.getElementById('imageDropZone')
image_viewer_container = document.getElementById('imageViewerContainer')
loaded_image = document.getElementById('loadedImage')
image_canvas = document.getElementById('imageCanvas')
analyze_image_btn = document.getElementById('analyzeImage')
change_image_btn = document.getElementById('changeImage')

# =============================================================================
# ESTADO GLOBAL
# =============================================================================

# Estado da aba atual
current_tab = "webcam"

# Estado webcam
stream = None
is_processing = False
processing_task = None
available_cameras = []
is_webcam_paused = False  # Webcam pausada manualmente

# Estado gravação webcam
media_recorder = None
recorded_chunks = []
webcam_captions = []
recording_start_time = None
last_caption_time = None

# Estado vídeo local
video_captions = []
video_processing_start_time = None
video_last_caption_time = None
is_video_processing = False
is_loop_enabled = False  # Repetição do vídeo

# Estado imagem
current_image_base64 = None


# =============================================================================
# FUNÇÕES DE CONFIGURAÇÃO
# =============================================================================

def update_base_url(event):
    """Atualiza a URL base quando o provedor muda."""
    provider = api_provider.value
    if provider == 'llamacpp':
        base_url.value = 'http://localhost:8080'
    elif provider == 'lmstudio':
        base_url.value = 'http://localhost:1234'


# =============================================================================
# SISTEMA DE ABAS
# =============================================================================

def switch_tab(event):
    """Alterna entre as abas."""
    global current_tab
    
    old_tab = current_tab
    
    # Para processamento ao trocar de aba
    if is_processing:
        handle_stop()
    
    # Obtém a aba clicada
    clicked_btn = event.target
    tab_name = clicked_btn.getAttribute('data-tab')
    
    if tab_name == old_tab:
        return
    
    # Pausa webcam ao sair da aba webcam
    if old_tab == "webcam" and stream is not None:
        pause_webcam()
    
    current_tab = tab_name
    
    # Atualiza botões
    tab_buttons = document.querySelectorAll('.tab-btn')
    for i in range(tab_buttons.length):
        btn = tab_buttons[i]
        if btn.getAttribute('data-tab') == tab_name:
            btn.classList.add('active')
        else:
            btn.classList.remove('active')
    
    # Atualiza painéis
    panels = document.querySelectorAll('.tab-panel')
    for i in range(panels.length):
        panel = panels[i]
        if panel.id == f"tab-{tab_name}":
            panel.classList.remove('hidden')
            panel.classList.add('active')
        else:
            panel.classList.add('hidden')
            panel.classList.remove('active')
    
    # Atualiza texto do botão Start conforme a aba
    if tab_name == "image":
        start_button.textContent = "Analisar"
        interval_select.disabled = True
    else:
        start_button.textContent = "Start"
        interval_select.disabled = False
    
    # Retoma webcam ao voltar para aba webcam
    if tab_name == "webcam" and stream is None:
        asyncio.ensure_future(resume_webcam())
    
    console.log(f"Switched to tab: {tab_name}")


# =============================================================================
# FUNÇÕES DE API
# =============================================================================

async def send_chat_completion_request(instruction: str, image_base64_url: str) -> str:
    """Envia requisição para a API de chat completion com imagem."""
    try:
        url = f"{base_url.value}/v1/chat/completions"
        
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
        
        js_payload = to_js(payload, dict_converter=Object.fromEntries)
        headers = to_js({"Content-Type": "application/json"}, dict_converter=Object.fromEntries)
        
        options = to_js({
            "method": "POST",
            "headers": headers,
            "body": JSON.stringify(js_payload)
        }, dict_converter=Object.fromEntries)
        
        response = await fetch(url, options)
        
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
        
        data_text = await response.text()
        data = json.loads(data_text)
        
        if 'choices' not in data or len(data['choices']) == 0:
            return "Error: Invalid response format"
        if 'message' not in data['choices'][0]:
            return "Error: Invalid response format"
        
        return data['choices'][0]['message']['content']
        
    except Exception as e:
        console.log(f"Error in request: {str(e)}")
        return f"Error: {str(e)}"


# =============================================================================
# FUNÇÕES DE CÂMERA (WEBCAM)
# =============================================================================

async def enumerate_cameras():
    """Enumera todas as câmeras disponíveis."""
    global available_cameras
    
    console.log("Starting camera enumeration...")
    
    try:
        while camera_select.options.length > 0:
            camera_select.remove(0)
        
        console.log("Requesting camera permission...")
        temp_constraints = to_js({"video": True, "audio": False}, dict_converter=Object.fromEntries)
        temp_stream = await navigator.mediaDevices.getUserMedia(temp_constraints)
        
        console.log("Permission granted, stopping temp stream...")
        tracks = temp_stream.getTracks()
        for i in range(tracks.length):
            tracks[i].stop()
        
        console.log("Enumerating devices...")
        devices = await navigator.mediaDevices.enumerateDevices()
        console.log(f"Total devices found: {devices.length}")
        
        available_cameras = []
        
        for i in range(devices.length):
            device = devices[i]
            if device.kind == "videoinput":
                device_id = device.deviceId
                label = device.label if device.label else f"Câmera {len(available_cameras) + 1}"
                
                available_cameras.append({
                    "deviceId": device_id,
                    "label": label
                })
                
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
        while camera_select.options.length > 0:
            camera_select.remove(0)
        option = document.createElement("option")
        option.value = ""
        option.textContent = f"Erro: {str(e)}"
        camera_select.appendChild(option)


async def switch_camera(device_id: str = None):
    """Troca para uma câmera específica."""
    global stream
    
    try:
        if stream:
            tracks = stream.getTracks()
            for i in range(tracks.length):
                tracks[i].stop()
        
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
        
        stream = await navigator.mediaDevices.getUserMedia(constraints)
        video.srcObject = stream
        
        response_text.value = "Câmera alterada com sucesso."
        console.log(f"Switched to camera: {device_id}")
        
    except Exception as e:
        error_msg = f"Erro ao trocar câmera: {str(e)}"
        console.error(error_msg)
        response_text.value = error_msg


def on_camera_change(event):
    """Callback quando o usuário seleciona outra câmera."""
    device_id = camera_select.value
    if device_id:
        asyncio.ensure_future(switch_camera(device_id))


async def init_camera():
    """Inicializa a webcam."""
    global stream
    
    try:
        await enumerate_cameras()
        
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


def capture_webcam_frame() -> str:
    """Captura frame da webcam como base64."""
    global stream
    if stream is None or video.videoWidth == 0:
        return None
    
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context = canvas.getContext('2d')
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.8)


def pause_webcam():
    """Pausa a webcam (para o stream)."""
    global stream, is_webcam_paused
    
    if stream is not None:
        tracks = stream.getTracks()
        for i in range(tracks.length):
            tracks[i].stop()
        stream = None
        is_webcam_paused = True
        video.classList.add('paused')
        toggle_webcam_btn.innerHTML = "&#x25B6; Retomar Webcam"
        console.log("Webcam paused")


async def resume_webcam():
    """Retoma a webcam."""
    global is_webcam_paused
    
    if len(available_cameras) > 0:
        await switch_camera(camera_select.value or available_cameras[0]["deviceId"])
        is_webcam_paused = False
        video.classList.remove('paused')
        toggle_webcam_btn.innerHTML = "&#x23F8; Pausar Webcam"
        console.log("Webcam resumed")


def toggle_webcam(event):
    """Alterna entre pausar e retomar webcam."""
    global stream
    
    if stream is not None:
        pause_webcam()
    else:
        asyncio.ensure_future(resume_webcam())


# =============================================================================
# FUNÇÕES DE LEGENDAS (SRT)
# =============================================================================

def format_time_srt(seconds: float) -> str:
    """Formata tempo para formato SRT (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_time_display(seconds: float) -> str:
    """Formata tempo para exibição (MM:SS)."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def add_webcam_caption(text: str):
    """Adiciona legenda da webcam."""
    global webcam_captions, recording_start_time, last_caption_time
    
    if recording_start_time is None:
        return
    
    current_time = window.performance.now() / 1000
    elapsed = current_time - recording_start_time
    
    start_time = last_caption_time if last_caption_time else elapsed
    end_time = elapsed
    
    if end_time > start_time and text and not text.startswith("Error"):
        webcam_captions.append({
            "start": start_time,
            "end": end_time,
            "text": text.strip()
        })
    
    last_caption_time = elapsed


def add_video_caption(text: str):
    """Adiciona legenda do vídeo local."""
    global video_captions, video_last_caption_time
    
    current_time = local_video.currentTime
    
    start_time = video_last_caption_time if video_last_caption_time else current_time
    end_time = current_time
    
    if end_time > start_time and text and not text.startswith("Error"):
        video_captions.append({
            "start": start_time,
            "end": end_time,
            "text": text.strip()
        })
    
    video_last_caption_time = current_time


def generate_srt_content(captions_list) -> str:
    """Gera conteúdo SRT a partir de lista de legendas."""
    srt_lines = []
    
    for i, caption in enumerate(captions_list, 1):
        start = format_time_srt(caption["start"])
        end = format_time_srt(caption["end"])
        text = caption["text"]
        
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")
    
    return "\n".join(srt_lines)


# =============================================================================
# FUNÇÕES DE GRAVAÇÃO (WEBCAM)
# =============================================================================

def on_data_available(event):
    """Callback quando dados de gravação estão disponíveis."""
    global recorded_chunks
    if event.data and event.data.size > 0:
        recorded_chunks.append(event.data)


def start_webcam_recording():
    """Inicia gravação da webcam."""
    global media_recorder, recorded_chunks, webcam_captions, recording_start_time, last_caption_time
    
    if stream is None:
        return
    
    recorded_chunks = []
    webcam_captions = []
    last_caption_time = None
    
    options = to_js({"mimeType": "video/webm;codecs=vp9"}, dict_converter=Object.fromEntries)
    
    try:
        media_recorder = window.MediaRecorder.new(stream, options)
    except:
        options = to_js({"mimeType": "video/webm"}, dict_converter=Object.fromEntries)
        media_recorder = window.MediaRecorder.new(stream, options)
    
    media_recorder.ondataavailable = create_proxy(on_data_available)
    media_recorder.start(1000)
    
    recording_start_time = window.performance.now() / 1000
    
    recording_indicator.classList.remove('hidden')
    video.classList.add('recording')
    download_section.classList.add('hidden')
    
    console.log("Webcam recording started")


def stop_webcam_recording():
    """Para gravação da webcam."""
    global media_recorder, recording_start_time
    
    if media_recorder and media_recorder.state != "inactive":
        media_recorder.stop()
    
    recording_start_time = None
    
    recording_indicator.classList.add('hidden')
    video.classList.remove('recording')
    
    window.setTimeout(create_proxy(lambda: download_section.classList.remove('hidden')), 500)
    
    console.log("Webcam recording stopped")


def download_webcam_video(event):
    """Download do vídeo da webcam."""
    global recorded_chunks
    
    if len(recorded_chunks) == 0:
        window.alert("Nenhum vídeo gravado!")
        return
    
    js_chunks = to_js(recorded_chunks)
    blob = Blob.new(js_chunks, to_js({"type": "video/webm"}, dict_converter=Object.fromEntries))
    
    url = URL.createObjectURL(blob)
    a = document.createElement('a')
    a.href = url
    a.download = "webcam_recording.webm"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)


def download_webcam_captions(event):
    """Download das legendas da webcam."""
    global webcam_captions
    
    if len(webcam_captions) == 0:
        window.alert("Nenhuma legenda gerada!")
        return
    
    srt_content = generate_srt_content(webcam_captions)
    
    blob = Blob.new(
        to_js([srt_content]),
        to_js({"type": "text/plain"}, dict_converter=Object.fromEntries)
    )
    
    url = URL.createObjectURL(blob)
    a = document.createElement('a')
    a.href = url
    a.download = "webcam_captions.srt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)


# =============================================================================
# FUNÇÕES DE VÍDEO LOCAL
# =============================================================================

def on_video_file_selected(event):
    """Callback quando arquivo de vídeo é selecionado."""
    files = video_file_input.files
    if files.length > 0:
        load_video_file(files.item(0))


def load_video_file(file):
    """Carrega arquivo de vídeo."""
    global video_captions, video_last_caption_time
    
    video_captions = []
    video_last_caption_time = None
    
    url = URL.createObjectURL(file)
    local_video.src = url
    
    video_drop_zone.classList.add('hidden')
    video_player_container.classList.remove('hidden')
    video_download_section.classList.add('hidden')
    
    console.log(f"Video loaded: {file.name}")


def on_video_loaded_metadata(event):
    """Callback quando metadados do vídeo são carregados."""
    video_timeline.max = local_video.duration
    total_time_display.textContent = format_time_display(local_video.duration)
    current_time_display.textContent = "00:00"
    console.log(f"Video duration: {local_video.duration}s")


def on_video_time_update(event):
    """Callback quando tempo do vídeo muda."""
    video_timeline.value = local_video.currentTime
    current_time_display.textContent = format_time_display(local_video.currentTime)


def on_timeline_change(event):
    """Callback quando timeline é arrastada."""
    local_video.currentTime = float(video_timeline.value)


def toggle_play_pause(event):
    """Alterna play/pause do vídeo."""
    if local_video.paused:
        local_video.play()
        play_pause_btn.textContent = "⏸️"
    else:
        local_video.pause()
        play_pause_btn.textContent = "▶️"


def stop_local_video(event):
    """Para o vídeo e volta ao início."""
    local_video.pause()
    local_video.currentTime = 0
    play_pause_btn.textContent = "▶️"


def prev_frame(event):
    """Retrocede 1 frame (~33ms para 30fps)."""
    local_video.pause()
    local_video.currentTime = max(0, local_video.currentTime - 0.033)
    play_pause_btn.textContent = "▶️"


def next_frame(event):
    """Avança 1 frame (~33ms para 30fps)."""
    local_video.pause()
    local_video.currentTime = min(local_video.duration, local_video.currentTime + 0.033)
    play_pause_btn.textContent = "▶️"


def rewind_video(event):
    """Retrocede 5 segundos."""
    local_video.currentTime = max(0, local_video.currentTime - 5)


def forward_video(event):
    """Avança 5 segundos."""
    local_video.currentTime = min(local_video.duration, local_video.currentTime + 5)


def change_playback_speed(event):
    """Altera velocidade de reprodução."""
    local_video.playbackRate = float(playback_speed_select.value)
    console.log(f"Playback speed: {playback_speed_select.value}x")


def toggle_loop(event):
    """Alterna repetição do vídeo."""
    global is_loop_enabled
    
    is_loop_enabled = not is_loop_enabled
    local_video.loop = is_loop_enabled
    
    if is_loop_enabled:
        toggle_loop_btn.classList.add('loop-active')
        console.log("Loop enabled")
    else:
        toggle_loop_btn.classList.remove('loop-active')
        console.log("Loop disabled")


def on_video_ended(event):
    """Callback quando o vídeo termina."""
    play_pause_btn.textContent = "▶️"
    if not is_loop_enabled:
        console.log("Video ended")


def show_video_upload(event):
    """Mostra área de upload de vídeo."""
    video_player_container.classList.add('hidden')
    video_drop_zone.classList.remove('hidden')
    video_download_section.classList.add('hidden')


def capture_local_video_frame() -> str:
    """Captura frame do vídeo local como base64."""
    if local_video.videoWidth == 0:
        return None
    
    local_video_canvas.width = local_video.videoWidth
    local_video_canvas.height = local_video.videoHeight
    context = local_video_canvas.getContext('2d')
    context.drawImage(local_video, 0, 0, local_video_canvas.width, local_video_canvas.height)
    return local_video_canvas.toDataURL('image/jpeg', 0.8)


def download_video_captions(event):
    """Download das legendas do vídeo local."""
    global video_captions
    
    if len(video_captions) == 0:
        window.alert("Nenhuma legenda gerada!")
        return
    
    srt_content = generate_srt_content(video_captions)
    
    blob = Blob.new(
        to_js([srt_content]),
        to_js({"type": "text/plain"}, dict_converter=Object.fromEntries)
    )
    
    url = URL.createObjectURL(blob)
    a = document.createElement('a')
    a.href = url
    a.download = "video_captions.srt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)


# =============================================================================
# FUNÇÕES DE IMAGEM
# =============================================================================

def on_image_file_selected(event):
    """Callback quando arquivo de imagem é selecionado."""
    files = image_file_input.files
    if files.length > 0:
        load_image_file(files.item(0))


def load_image_file(file):
    """Carrega arquivo de imagem."""
    global current_image_base64
    
    reader = FileReader.new()
    
    def on_load(e):
        global current_image_base64
        current_image_base64 = reader.result
        loaded_image.src = current_image_base64
        
        image_drop_zone.classList.add('hidden')
        image_viewer_container.classList.remove('hidden')
        
        console.log(f"Image loaded: {file.name}")
    
    reader.onload = create_proxy(on_load)
    reader.readAsDataURL(file)


def show_image_upload(event):
    """Mostra área de upload de imagem."""
    image_viewer_container.classList.add('hidden')
    image_drop_zone.classList.remove('hidden')


async def analyze_current_image():
    """Analisa a imagem carregada."""
    global current_image_base64
    
    if current_image_base64 is None:
        response_text.value = "Nenhuma imagem carregada."
        return
    
    response_text.value = "Analisando imagem..."
    
    instruction = instruction_text.value
    response = await send_chat_completion_request(instruction, current_image_base64)
    response_text.value = response


def on_analyze_image_click(event):
    """Callback do botão de análise de imagem."""
    asyncio.ensure_future(analyze_current_image())


# =============================================================================
# DRAG & DROP
# =============================================================================

def setup_drag_drop(drop_zone, file_input, file_handler):
    """Configura drag & drop para uma área."""
    
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


# =============================================================================
# LOOP DE PROCESSAMENTO
# =============================================================================

async def send_data():
    """Processa frame conforme a aba atual."""
    global is_processing
    
    if not is_processing:
        return
    
    instruction = instruction_text.value
    image_base64 = None
    
    if current_tab == "webcam":
        image_base64 = capture_webcam_frame()
    elif current_tab == "video":
        image_base64 = capture_local_video_frame()
    
    if image_base64 is None:
        response_text.value = "Falha ao capturar frame."
        return
    
    response = await send_chat_completion_request(instruction, image_base64)
    response_text.value = response
    
    # Adiciona legenda
    if current_tab == "webcam" and enable_recording.checked and recording_start_time is not None:
        add_webcam_caption(response)
    elif current_tab == "video":
        add_video_caption(response)


async def processing_loop():
    """Loop principal de processamento."""
    global is_processing
    
    interval_ms = int(interval_select.value)
    interval_s = interval_ms / 1000.0
    
    while is_processing:
        await send_data()
        await asyncio.sleep(interval_s)


# =============================================================================
# CONTROLES DE INÍCIO/PARADA
# =============================================================================

def handle_start():
    """Inicia o processamento."""
    global is_processing, processing_task, video_captions, video_last_caption_time
    
    # Validações
    url_value = base_url.value
    if not (url_value.startswith('http://') or url_value.startswith('https://')):
        response_text.value = "URL inválida. Use http:// ou https://"
        return
    
    if current_tab == "webcam":
        if stream is None:
            response_text.value = "Câmera não disponível."
            return
    elif current_tab == "video":
        if local_video.src == "":
            response_text.value = "Nenhum vídeo carregado."
            return
        # Reseta legendas do vídeo
        video_captions = []
        video_last_caption_time = None
        # Inicia o vídeo
        local_video.play()
        play_pause_btn.textContent = "⏸️"
    elif current_tab == "image":
        # Para imagem, faz análise única
        asyncio.ensure_future(analyze_current_image())
        return
    
    is_processing = True
    start_button.textContent = "Stop"
    start_button.classList.remove('start')
    start_button.classList.add('stop')
    
    # Desabilita controles
    instruction_text.disabled = True
    interval_select.disabled = True
    api_provider.disabled = True
    base_url.disabled = True
    
    if current_tab == "webcam":
        enable_recording.disabled = True
        if enable_recording.checked:
            start_webcam_recording()
    
    response_text.value = "Processando..."
    
    processing_task = asyncio.ensure_future(processing_loop())


def handle_stop():
    """Para o processamento."""
    global is_processing, processing_task
    
    is_processing = False
    
    if processing_task:
        processing_task.cancel()
        processing_task = None
    
    start_button.textContent = "Start" if current_tab != "image" else "Analisar"
    start_button.classList.remove('stop')
    start_button.classList.add('start')
    
    # Reabilita controles
    instruction_text.disabled = False
    interval_select.disabled = current_tab == "image"
    api_provider.disabled = False
    base_url.disabled = False
    
    if current_tab == "webcam":
        enable_recording.disabled = False
        if enable_recording.checked:
            stop_webcam_recording()
    elif current_tab == "video":
        local_video.pause()
        play_pause_btn.textContent = "▶️"
        # Mostra download de legendas
        if len(video_captions) > 0:
            video_download_section.classList.remove('hidden')
    
    if response_text.value == "Processando...":
        response_text.value = "Processamento parado."


def toggle_processing(event):
    """Alterna entre iniciar e parar."""
    global is_processing
    if is_processing:
        handle_stop()
    else:
        handle_start()


# =============================================================================
# ATALHOS DE TECLADO
# =============================================================================

def on_keydown(event):
    """Trata atalhos de teclado."""
    # Ignora se estiver digitando em input/textarea
    tag = event.target.tagName.lower()
    if tag in ['input', 'textarea', 'select']:
        return
    
    key = event.key
    
    if current_tab == "video":
        if key == " ":  # Espaço = Play/Pause
            event.preventDefault()
            toggle_play_pause(event)
        elif key == "ArrowLeft":  # Seta esquerda = Frame anterior
            event.preventDefault()
            prev_frame(event)
        elif key == "ArrowRight":  # Seta direita = Próximo frame
            event.preventDefault()
            next_frame(event)


# =============================================================================
# LIMPEZA DE RECURSOS
# =============================================================================

def cleanup(event):
    """Limpa recursos ao sair da página."""
    global stream, is_processing
    
    is_processing = False
    
    if stream:
        tracks = stream.getTracks()
        for i in range(tracks.length):
            tracks[i].stop()


# =============================================================================
# REGISTRO DE EVENT LISTENERS
# =============================================================================

# Abas
tab_buttons = document.querySelectorAll('.tab-btn')
for i in range(tab_buttons.length):
    tab_buttons[i].addEventListener('click', create_proxy(switch_tab))

# Controles comuns
api_provider.addEventListener('change', create_proxy(update_base_url))
start_button.addEventListener('click', create_proxy(toggle_processing))

# Webcam
camera_select.addEventListener('change', create_proxy(on_camera_change))
download_video_btn.addEventListener('click', create_proxy(download_webcam_video))
download_captions_btn.addEventListener('click', create_proxy(download_webcam_captions))
toggle_webcam_btn.addEventListener('click', create_proxy(toggle_webcam))

# Vídeo local
video_file_input.addEventListener('change', create_proxy(on_video_file_selected))
local_video.addEventListener('loadedmetadata', create_proxy(on_video_loaded_metadata))
local_video.addEventListener('timeupdate', create_proxy(on_video_time_update))
video_timeline.addEventListener('input', create_proxy(on_timeline_change))
play_pause_btn.addEventListener('click', create_proxy(toggle_play_pause))
stop_video_btn.addEventListener('click', create_proxy(stop_local_video))
prev_frame_btn.addEventListener('click', create_proxy(prev_frame))
next_frame_btn.addEventListener('click', create_proxy(next_frame))
rewind_btn.addEventListener('click', create_proxy(rewind_video))
forward_btn.addEventListener('click', create_proxy(forward_video))
playback_speed_select.addEventListener('change', create_proxy(change_playback_speed))
change_video_btn.addEventListener('click', create_proxy(show_video_upload))
download_video_srt_btn.addEventListener('click', create_proxy(download_video_captions))
toggle_loop_btn.addEventListener('click', create_proxy(toggle_loop))
local_video.addEventListener('ended', create_proxy(on_video_ended))

# Imagem
image_file_input.addEventListener('change', create_proxy(on_image_file_selected))
analyze_image_btn.addEventListener('click', create_proxy(on_analyze_image_click))
change_image_btn.addEventListener('click', create_proxy(show_image_upload))

# Drag & Drop
setup_drag_drop(video_drop_zone, video_file_input, load_video_file)
setup_drag_drop(image_drop_zone, image_file_input, load_image_file)

# Atalhos de teclado
document.addEventListener('keydown', create_proxy(on_keydown))

# Limpeza
window.addEventListener('beforeunload', create_proxy(cleanup))


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

async def main():
    """Função principal de inicialização."""
    await init_camera()
    loading_overlay.classList.add('hidden')
    console.log("Vision AI App initialized!")


asyncio.ensure_future(main())
