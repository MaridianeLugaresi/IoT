import paho.mqtt.client as mqtt
import time
import json
import random
import threading # Módulo para rodar as 4 conexões em paralelo

# ====================
# CONFIGURAÇÕES GLOBAIS
# ====================
THINGSBOARD_HOST = 'mqtt.thingsboard.cloud' 
THINGSBOARD_PORT = 1883
TELEMETRY_TOPIC = 'v1/devices/me/telemetry'

# ====================
# CLASSE PARA CADA DISPOSITIVO (SENSOR)
# ====================

class SensorDevice(threading.Thread):
    def __init__(self, name, access_token, data_key, min_limit, max_limit, initial_value):
        # Inicializa a Thread e os atributos do dispositivo
        super().__init__()
        self.name = name
        self.access_token = access_token
        self.data_key = data_key  # Ex: "temperatura", "umidade", etc.
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.ultima_leitura_valida = initial_value
        
        # Cria um cliente MQTT ÚNICO para esta thread/dispositivo
        self.client = mqtt.Client(client_id=f"Client-{name}")
        self.client.on_connect = self.on_connect
        self.client.username_pw_set(self.access_token)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{self.name}] CONECTADO ao ThingsBoard.")
        else:
            print(f"[{self.name}] FALHA NA CONEXÃO, código {rc}")

    def generate_data(self):
        """Gera um valor com variação e chance de outlier."""
        
        # Gera valor baseado na última leitura válida
        raw_value = self.ultima_leitura_valida + random.uniform(-1.0, 1.0)
        
        # 5% de chance de Outlier
        if random.random() < 0.05:
            if random.choice([True, False]):
                raw_value = random.uniform(self.max_limit + 5, self.max_limit + 10)  # Outlier Alto
            else:
                raw_value = random.uniform(self.min_limit - 5, self.min_limit - 10) # Outlier Baixo
                
        return raw_value

    def filter_outlier(self, raw_value):
        """REQUISITO B: Aplica o filtro de outlier."""
        
        if raw_value > self.max_limit or raw_value < self.min_limit:
            # Se for outlier, usa a última leitura válida
            processed_value = self.ultima_leitura_valida
            print(f"[{self.name}] [OUTLIER] Original: {raw_value:.2f}. Enviando: {processed_value:.2f}")
        else:
            # Se for válido, atualiza e usa o valor original
            self.ultima_leitura_valida = raw_value
            processed_value = raw_value
            # print(f"[{self.name}] [VÁLIDO] Valor: {processed_value:.2f}") # Remova o comentário para ver todos os envios
            
        return round(processed_value, 2)
    
    def run(self):
        """O Loop principal da Thread para este dispositivo."""
        
        try:
            # Conecta o cliente MQTT específico desta thread
            self.client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
            self.client.loop_start() # Inicia o loop em segundo plano para esta conexão
            
            while True:
                # 1. Geração e Processamento de Dados
                raw_data = self.generate_data()
                processed_data = self.filter_outlier(raw_data)
                
                # 2. Criação do Payload
                telemetry_data = {
                    self.data_key: processed_data # A chave é dinâmica: "temp_rack", "umidade_ar", etc.
                }
                payload = json.dumps(telemetry_data)
                
                # 3. Envio
                self.client.publish(TELEMETRY_TOPIC, payload, qos=1)
                
                time.sleep(random.randint(4, 7)) # Intervalo aleatório entre 4 e 7 segundos
                
        except KeyboardInterrupt:
            self.client.loop_stop()
            self.client.disconnect()
            print(f"\n[{self.name}] Simulação encerrada.")


# ====================
# INICIALIZAÇÃO DOS 4 DISPOSITIVOS (REQUISITO A)
# ====================

if __name__ == '__main__':
    
    print("Iniciando Simulação Distribuída de 4 Dispositivos IoT...")

    # ATENÇÃO: SUBSTITUA 'TOKEN_X' PELOS 4 TOKENS REAIS DO THINGSBOARD
    devices = [
        # D1: Servidor Principal - Temperatura
        SensorDevice(
            name="ServidorPrincipal", 
            access_token="q35VjYD6kkq7wBoF2taa", 
            data_key="temp_rack",
            min_limit=15.0, 
            max_limit=40.0, 
            initial_value=25.0
        ),
        
        # D2: Entrada de Ar - Umidade
        SensorDevice(
            name="EntradaAr", 
            access_token="uekn6jmw6cwtm4xtdq5m", 
            data_key="umidade_ar",
            min_limit=40.0, 
            max_limit=80.0, 
            initial_value=60.0
        ),
        
        # D3: Estabilizador - Vibração
        SensorDevice(
            name="Estabilizador", 
            access_token="Z5JbjXLkzMmy8ekI3yzI", 
            data_key="vibracao_fan",
            min_limit=10.0, 
            max_limit=800.0, 
            initial_value=300.0
        ),
        
        # D4: Iluminação - Luminosidade
        SensorDevice(
            name="Iluminacao", 
            access_token="80Cci9DgxUvLzYYFStps", 
            data_key="lux",
            min_limit=50.0, 
            max_limit=900.0, 
            initial_value=500.0
        )
    ]

    # Inicia todas as threads (dispositivos)
    for device in devices:
        device.start()
        
    try:
        # Mantém o script principal rodando até que todas as threads terminem (ou Ctrl+C)
        for device in devices:
            device.join() 
            
    except KeyboardInterrupt:
        print("\n\nEncerrando todas as threads (dispositivos)...")
        # As threads serão encerradas dentro do loop 'run'
        pass