import paho.mqtt.client as mqtt
import time
import json
import random
import threading
import sys

# ====================
# CONFIGURAÇÕES GLOBAIS
# ====================
THINGSBOARD_HOST = 'mqtt.thingsboard.cloud' 
THINGSBOARD_PORT = 1883
TELEMETRY_TOPIC = 'v1/devices/me/telemetry'

# Flag de evento para sinalizar a todas as threads para parar
stop_event = threading.Event() 

# ====================
# CLASSE PARA CADA DISPOSITIVO (SENSOR)
# ====================

class SensorDevice(threading.Thread):
    def __init__(self, name, access_token, data_key, min_limit, max_limit, initial_value, is_binary=False):
        
        super().__init__()
        self.name = name
        self.access_token = access_token
        self.data_key = data_key  
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.ultima_leitura_valida = initial_value
        self.is_binary = is_binary
        
        self.client = mqtt.Client(client_id=f"Client-{name}")
        self.client.on_connect = self.on_connect

        self.client.username_pw_set(self.access_token)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{self.name}] CONECTADO ao ThingsBoard.")
        else:
            print(f"[{self.name}] FALHA NA CONEXÃO, código {rc}. Tentando reconexão...")
            stop_event.set()

    def generate_data(self):
        """Gera um valor com variação e chance de dar outlier."""
        
        if self.is_binary:
            # Para sensores binários (como vazamento): 98% de chance de 0, 2% de chance de 1
            if random.random() < 0.02:
                raw_value = 1 # Vazamento detectado
            else:
                raw_value = 0 # Normal
            
            # 1% de chance de outlier (valor diferente de 0 ou 1)
            if random.random() < 0.01:
                 raw_value = random.choice([2, -1, 99]) # Outlier
            
            return raw_value
        
        # Para sensores contínuos
        raw_value = self.ultima_leitura_valida + random.uniform(-1.0, 1.0)
        
        # 5% de chance de Outlier
        if random.random() < 0.05:
            if random.choice([True, False]):
                raw_value = random.uniform(self.max_limit + 5, self.max_limit + 10)  # Outlier Alto
            else:
                raw_value = random.uniform(self.min_limit - 5, self.min_limit - 10) # Outlier Baixo
                
        return raw_value

    def filter_outlier(self, raw_value):
        """REQUISITO B: Aplica o filtro de outlier (processamento local)."""
        
        # Lógica especial para sensor Binário (Vazamento)
        if self.is_binary:
            if raw_value not in [0, 1]:
                # Outlier: Deve ser 0 ou 1. Assume-se que a última leitura válida é 0 (Sem vazamento)
                processed_value = 0 
                print(f"[{self.name}] [OUTLIER BINÁRIO] Original: {raw_value}. Enviando: {processed_value}")
                return processed_value
            
            # Atualiza a última leitura válida, se necessário
            self.ultima_leitura_valida = raw_value
            return raw_value
            
        
        # Lógica para sensores Contínuos (Temperatura, Umidade, Vibração)
        if raw_value > self.max_limit or raw_value < self.min_limit:
            # Se for outlier, usa a última leitura válida
            processed_value = self.ultima_leitura_valida
            print(f"[{self.name}] [OUTLIER] Original: {raw_value:.2f}. Enviando: {processed_value:.2f}")
        else:
            # Se for válido, atualiza e usa o valor original
            self.ultima_leitura_valida = raw_value
            processed_value = raw_value
            
        return round(processed_value, 2)
    
    def run(self):
        
        try:
            self.client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
            self.client.loop_start() 
            
            while not stop_event.is_set():
                
                # 1. Geração e Processamento de Dados
                raw_data = self.generate_data()
                processed_data = self.filter_outlier(raw_data)
                
                # 2. Criação e Envio do Payload
                telemetry_data = { self.data_key: processed_data }
                payload = json.dumps(telemetry_data)
                
                self.client.publish(TELEMETRY_TOPIC, payload, qos=1)
                
                # Vazamento é muito crítico, envie um pouco mais rápido
                if self.is_binary:
                    stop_event.wait(timeout=random.randint(1, 3)) 
                else:
                    stop_event.wait(timeout=random.randint(4, 7))

        except Exception as e:
            print(f"[{self.name}] Erro inesperado: {e}")
            
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print(f"[{self.name}] Encerrado e desconectado.")


# ====================
# INICIALIZAÇÃO E CONTROLE CENTRAL (REQUISITO A)
# ====================

if __name__ == '__main__':
    
    print("Iniciando Simulação Distribuída de 4 Dispositivos IoT...")

    devices = [
        # D1: Servidor Principal - Temperatura (Limites refinados: 10C a 50C)
        SensorDevice(
            name="ServidorPrincipal", 
            access_token="q35VjYD6kkq7wBoF2taa", 
            data_key="temp_rack",
            min_limit=10.0, max_limit=50.0, initial_value=25.0
        ),
        
        # D2: Entrada de Ar - Umidade (Limites refinados: 20% a 90%)
        SensorDevice(
            name="EntradaAr", 
            access_token="uekn6jmw6cwtm4xtdq5m", 
            data_key="umidade_ar",
            min_limit=20.0, max_limit=90.0, initial_value=60.0
        ),
        
        # D3: Estabilizador - Vibração (Limites refinados: 5 a 1500)
        SensorDevice(
            name="Estabilizador", 
            access_token="Z5JbjXLkzMmy8ekI3yzI", 
            data_key="vibracao_fan",
            min_limit=5.0, max_limit=1500.0, initial_value=300.0
        ),
        
        # D4: DETECTOR DE VAZAMENTO DE ÁGUA (Novo Dispositivo Crítico)
        SensorDevice(
            name="DetectorAgua", 
            access_token="23bfivmrl0lc9rym66rg", 
            data_key="vazamento_agua", # 0: Normal, 1: Vazamento
            min_limit=0, max_limit=1, initial_value=0, 
            is_binary=True # Indica que é um sensor binário
        )
    ]

    # Inicia todas as threads (dispositivos)
    for device in devices:
        device.start()
        
    try:
        # Loop para manter a thread principal viva e monitorar o Ctrl+C
        while not stop_event.is_set():
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\n\n[MAIN] Ctrl+C detectado. Sinalizando threads para parar...")
        stop_event.set()
        
    finally:
        for device in devices:
            device.join() 
            
        print("[MAIN] Todas as simulações encerradas. Script finalizado com sucesso.")
        sys.exit(0)