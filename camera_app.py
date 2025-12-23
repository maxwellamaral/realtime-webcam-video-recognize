"""
Camera Interaction App - PyScript Version
Aplicação de interação com câmera usando Python no navegador.
"""

from js import document, navigator, console, JSON, Object, window, fetch
from pyodide.ffi import create_proxy, to_js
import asyncio
import json

# Elementos do DOM
video = document.getElementById('videoFeed')
canvas = document.getElementById('canvas')
api_provider = document.getElementById('apiProvider')
base_url = document.getElementById('baseURL')
instruction_text = document.getElementById('instructionText')
response_text = document.getElementById('responseText')
interval_select = document.getElementById('intervalSelect')
start_button = document.getElementById('startButton')
loading_overlay = document.getElementById('loadingOverlay')

# Estado global
stream = None
is_processing = False
processing_task = None


def update_base_url(event):
    """Atualiza a URL base quando o provedor muda"""
    provider = api_provider.value
    if provider == 'llamacpp':
        base_url.value = 'http://localhost:8080'
    elif provider == 'lmstudio':
        base_url.value = 'http://localhost:1234'


async def send_chat_completion_request(instruction: str, image_base64_url: str) -> str:
    """Envia requisição para a API de chat completion"""
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
        
        # Converte payload para JavaScript object
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
                error_msg += " - Endpoint not found. Make sure the server is running."
            elif status == 500:
                error_msg += " - Server error. Check if the model supports vision."
            elif status in [400, 422]:
                error_msg += " - Invalid request format."
            
            return error_msg
        
        data_text = await response.text()
        data = json.loads(data_text)
        
        if 'choices' not in data or len(data['choices']) == 0:
            return "Error: Invalid response format from server"
        
        if 'message' not in data['choices'][0]:
            return "Error: Invalid response format from server"
        
        return data['choices'][0]['message']['content']
        
    except Exception as e:
        console.log(f"Error in request: {str(e)}")
        return f"Error: {str(e)}"


async def init_camera():
    """Inicializa a câmera"""
    global stream
    try:
        constraints = to_js({"video": True, "audio": False}, dict_converter=Object.fromEntries)
        stream = await navigator.mediaDevices.getUserMedia(constraints)
        video.srcObject = stream
        response_text.value = "Camera access granted. Ready to start."
        console.log("Camera initialized successfully")
    except Exception as e:
        error_msg = f"Error accessing camera: {str(e)}"
        console.error(error_msg)
        response_text.value = error_msg
        window.alert("Error accessing camera. Make sure you've granted permission.")


def capture_image() -> str:
    """Captura um frame do vídeo como base64"""
    global stream
    if stream is None or video.videoWidth == 0:
        console.warn("Video stream not ready for capture.")
        return None
    
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context = canvas.getContext('2d')
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.8)


async def send_data():
    """Captura imagem e envia para a API"""
    global is_processing
    if not is_processing:
        return
    
    instruction = instruction_text.value
    image_base64_url = capture_image()
    
    if image_base64_url is None:
        response_text.value = "Failed to capture image. Stream might not be active."
        return
    
    response = await send_chat_completion_request(instruction, image_base64_url)
    response_text.value = response


async def processing_loop():
    """Loop principal de processamento"""
    global is_processing
    interval_ms = int(interval_select.value)
    interval_s = interval_ms / 1000.0
    
    while is_processing:
        await send_data()
        await asyncio.sleep(interval_s)


def handle_start():
    """Inicia o processamento"""
    global is_processing, stream, processing_task
    
    if stream is None:
        response_text.value = "Camera not available. Cannot start."
        window.alert("Camera not available. Please grant permission first.")
        return
    
    # Valida URL base
    url_value = base_url.value
    if not (url_value.startswith('http://') or url_value.startswith('https://')):
        response_text.value = "Invalid base URL. Must start with http:// or https://"
        window.alert("Please enter a valid base URL (e.g., http://localhost:1234)")
        return
    
    is_processing = True
    start_button.textContent = "Stop"
    start_button.classList.remove('start')
    start_button.classList.add('stop')
    
    instruction_text.disabled = True
    interval_select.disabled = True
    api_provider.disabled = True
    base_url.disabled = True
    
    response_text.value = "Processing started..."
    
    # Inicia o loop de processamento
    processing_task = asyncio.ensure_future(processing_loop())


def handle_stop():
    """Para o processamento"""
    global is_processing, processing_task
    
    is_processing = False
    
    if processing_task:
        processing_task.cancel()
        processing_task = None
    
    start_button.textContent = "Start"
    start_button.classList.remove('stop')
    start_button.classList.add('start')
    
    instruction_text.disabled = False
    interval_select.disabled = False
    api_provider.disabled = False
    base_url.disabled = False
    
    if response_text.value.startswith("Processing started..."):
        response_text.value = "Processing stopped."


def toggle_processing(event):
    """Alterna entre iniciar e parar o processamento"""
    global is_processing
    if is_processing:
        handle_stop()
    else:
        handle_start()


def cleanup(event):
    """Limpa recursos ao sair da página"""
    global stream, is_processing
    is_processing = False
    if stream:
        tracks = stream.getTracks()
        for i in range(tracks.length):
            tracks[i].stop()


# Registra event listeners
api_provider.addEventListener('change', create_proxy(update_base_url))
start_button.addEventListener('click', create_proxy(toggle_processing))
window.addEventListener('beforeunload', create_proxy(cleanup))


async def main():
    """Função principal de inicialização"""
    await init_camera()
    loading_overlay.classList.add('hidden')
    console.log("PyScript Camera App initialized!")


# Inicia a aplicação
asyncio.ensure_future(main())
