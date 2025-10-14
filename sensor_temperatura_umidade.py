import paho.mqtt.client as mqtt
import time
import json
import random

# ====================
# 1. CONFIGURAÇÕES MQTT
# ====================

# Insira o IP ou endereço do seu Broker ThingsBoard.
# Para a versão Cloud do ThingsBoard, use: demo.thingsboard.io
THINGSBOARD_HOST = 'mqtt.thingsboard.cloud' 
THINGSBOARD_PORT = 1883  # Porta padrão MQTT

# SUBSTITUA PELO TOKEN DO SEU DISPOSITIVO NO THINGSBOARD
ACCESS_TOKEN = 'wp9412skt6okkgxmfgaa' 

# O ThingsBoard usa o tópico 'v1/devices/me/telemetry' para receber dados
TELEMETRY_TOPIC = 'v1/devices/me/telemetry'

# ====================
# 2. CONFIGURAÇÕES DO SENSOR E OUTLIER
# ====================

# Limites aceitáveis para a temperatura (para o algoritmo de outlier)
TEMP_MAX = 40.0
TEMP_MIN = 15.0

# Variável para armazenar a última leitura válida (para usar em caso de outlier)
ultima_temperatura_valida = 25.0

def generate_sensor_data():
    """Gera dados de temperatura e umidade com chance de outlier."""
    
    # Gera temperatura com pequena variação normal
    temp = ultima_temperatura_valida + random.uniform(-1.0, 1.0)
    
    # 5% de chance de gerar um outlier (leitura incorreta)
    if random.random() < 0.05:
        # Gera um valor fora do limite (simulação de erro de sensor)
        if random.choice([True, False]):
            temp = random.uniform(TEMP_MAX + 5, TEMP_MAX + 15)  # Outlier Alto
        else:
            temp = random.uniform(TEMP_MIN - 10, TEMP_MIN - 5)  # Outlier Baixo
            
    # Umidade (varia normalmente, sem outlier nesta simulação)
    humidity = random.uniform(50.0, 70.0) 
    
    return temp, humidity

def process_data_and_filter_outliers(temp, humidity):
    """
    REQUISITO B: Algoritmo de processamento local (eliminação de outliers).
    Verifica se a leitura está fora dos limites e aplica o filtro.
    """
    global ultima_temperatura_valida
    
    processed_temp = temp
    outlier_detected = False
    
    if temp > TEMP_MAX or temp < TEMP_MIN:
        outlier_detected = True
        # FILTRO: Substitui o outlier pela última leitura válida conhecida
        processed_temp = ultima_temperatura_valida
        print(f"  [OUTLIER DETECTADO] Valor original: {temp:.2f}°C. Enviando última leitura válida: {processed_temp:.2f}°C")
    else:
        # Se for válido, atualiza a última leitura válida
        ultima_temperatura_valida = processed_temp
        print(f"  [DADO VÁLIDO] Temperatura: {processed_temp:.2f}°C")
        
    return processed_temp, humidity

# ====================
# 3. FUNÇÕES MQTT
# ====================

def on_connect(client, userdata, flags, rc):
    """Callback chamado quando o cliente se conecta ao broker."""
    if rc == 0:
        print(f"Conectado ao ThingsBoard. Token: {ACCESS_TOKEN}")
    else:
        print(f"Falha na conexão, código {rc}")

# Cria o cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect

# Configuração de autenticação: o Token de Acesso é usado como Username
client.username_pw_set(ACCESS_TOKEN)

# Conexão ao broker
client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
client.loop_start()

# ====================
# 4. LOOP PRINCIPAL
# ====================
try:
    while True:
        # 1. Geração de Dados
        temp_raw, humidity_raw = generate_sensor_data()
        
        # 2. Processamento (Eliminação de Outlier)
        temp_processed, humidity_processed = process_data_and_filter_outliers(temp_raw, humidity_raw)
        
        # 3. Criação do Payload de Telemetria (JSON)
        telemetry_data = {
            "temperatura": round(temp_processed, 2),
            "umidade": round(humidity_processed, 2),
            "timestamp": int(time.time() * 1000) # O ThingsBoard também aceita o timestamp
        }
        
        # 4. Envio dos Dados via MQTT
        payload = json.dumps(telemetry_data)
        client.publish(TELEMETRY_TOPIC, payload, qos=1)
        
        print(f"Publicado no tópico {TELEMETRY_TOPIC}: {payload}")
        
        time.sleep(5) # Envia dados a cada 5 segundos

except KeyboardInterrupt:
    print("\nSimulação encerrada.")
    client.loop_stop()
    client.disconnect()