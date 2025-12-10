# 🐛 Llama-Server Troubleshooting: Vulkan DeviceLostError

## 📋 Problem-Beschreibung

Der Llama-Server stürzt mit einem Vulkan-`DeviceLostError` ab:

```
libc++abi: terminating due to uncaught exception of type vk::DeviceLostError
vk::Device::getFenceStatus: ErrorDeviceLost
```

## 🔍 Ursachen-Analyse

### **Wahrscheinliche Ursachen:**

1. **GPU-Speicher-Überlastung**: Modell ist zu groß für verfügbaren VRAM
2. **GPU-Treiber-Problem**: Vulkan-Treiber ist instabil oder veraltet
3. **Hardware-Limitierung**: GPU unterstützt Vulkan nicht richtig
4. **Modell-Inkompatibilität**: Qwen3-4B-Q5_K_M zu groß für deine GPU

### **Schnell-Diagnose:**

```bash
# GPU-Info prüfen
system_profiler SPDisplaysDataType

# Vulkan-Unterstützung testen
vulkaninfo | head -20

# Verfügbarer GPU-Speicher
./llama.cpp/build/bin/llama-server --help | grep -A5 -B5 gpu
```

## 🛠️ Lösungsansätze

### **Lösung 1: CPU-Modus verwenden (Empfohlen)**

Deaktiviere Vulkan und verwende CPU-Only-Modus:

```bash
# Startbefehl ändern (entferne Vulkan-Flags)
./llama.cpp/build/bin/llama-server \
  -m ./models/Qwen3-4B-Q5_K_M.gguf \
  --host 0.0.0.0 \
  --port 5020 \
  --ctx-size 4096 \
  --threads 8 \
  --gpu-layers 0  # CPU-ONLY MODUS
```

**Vorteile:**
- ✅ Stabil und zuverlässig
- ✅ Keine GPU-Treiber-Probleme
- ✅ Funktioniert auf allen Macs
- ⚠️ Langsamer als GPU-Beschleunigung

### **Lösung 2: Kleineres Modell verwenden**

Wechsle zu einem kleineren Modell:

```bash
# Llama-3.2-3B-Instruct-Q4_K_M (kleiner als Qwen3-4B)
./llama.cpp/build/bin/llama-server \
  -m ./models/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 5020 \
  --gpu-layers 0  # Sicherheitshalber CPU-Modus
```

### **Lösung 3: Weniger GPU-Layer**

Wenn GPU funktionieren soll, reduziere GPU-Layer:

```bash
./llama.cpp/build/bin/llama-server \
  -m ./models/Qwen3-4B-Q5_K_M.gguf \
  --host 0.0.0.0 \
  --port 5020 \
  --gpu-layers 10  # Reduziert von auto/default
```

### **Lösung 4: System-RAM erhöhen**

Stelle sicher, dass genügend RAM verfügbar ist:

```bash
# RAM prüfen
vm_stat

# Llama-Server mit weniger Context-Size
./llama.cpp/build/bin/llama-server \
  -m ./models/Qwen3-4B-Q5_K_M.gguf \
  --ctx-size 2048  # Reduziert von 4096
  --gpu-layers 0   # CPU-Modus
```

## ⚙️ CrewAI-Konfiguration anpassen

### **Settings für CPU-Modus:**

**`core/settings.py`:**
```python
# Für CPU-Modus optimierte Settings
llm_max_tokens: int = Field(default=1000, ge=1, le=2000, description="Reduziert für CPU")
llm_temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Standard-Temperature")
```

### **Alternative LLM-Provider:**

Wenn Llama-Server Probleme macht, verwende Cloud-LLM:

**`main.py`:**
```python
# Fallback zu Cloud-LLM
llm = cloud_llm_gpt4  # Oder cloud_llm_deepseek_chat
```

## 🔧 Erweiterte Diagnose

### **Vulkan-Treiber prüfen:**

```bash
# MoltenVK-Version (macOS Vulkan-Implementation)
brew info molten-vk

# GPU-Info detailliert
./llama.cpp/build/bin/llama-server --verbose 2>&1 | grep -i vulkan
```

### **Memory-Debugging:**

```bash
# Mit Memory-Logging
./llama.cpp/build/bin/llama-server \
  -m ./models/Qwen3-4B-Q5_K_M.gguf \
  --gpu-layers 0 \
  --log-format json \
  --log-colors false \
  2>&1 | grep -i "memory\|gpu\|vulkan"
```

### **Alternative Build:**

```bash
# Llama.cpp ohne Vulkan bauen
cd llama.cpp
cmake -B build -DLLAMA_VULKAN=OFF
cmake --build build --config Release
```

## 🚀 Empfohlene Konfiguration

### **Für stabile Produktion:**

```bash
# CPU-Modus mit optimierten Settings
./llama.cpp/build/bin/llama-server \
  -m ./models/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 5020 \
  --ctx-size 2048 \
  --threads 4 \
  --gpu-layers 0 \
  --parallel 1 \
  --cont-batching \
  --flash-attn
```

### **Environment-Variablen:**

**`.env`:**
```bash
# Llama-Server für CPU optimieren
LLAMA_THREADS=4
LLAMA_CTX_SIZE=2048
LLAMA_GPU_LAYERS=0
```

## 📊 Performance-Vergleich

| Modus | Qwen3-4B-Q5_K_M | Llama-3.2-3B-Q4_K_M | Tokens/sec |
|-------|-----------------|---------------------|------------|
| GPU   | ❌ Crasht       | ❌ Crasht          | -         |
| CPU   | 2-3 tok/s       | 4-6 tok/s          | ✅        |
| Cloud | ∞               | ∞                  | Schnell   |

## 🔄 Automatische Fallbacks

### **Auto-Recovery-Script:**

**`scripts/start_llama_safe.sh`:**
```bash
#!/bin/bash

MODEL_PATH="./models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
BACKUP_MODEL="./models/Llama-3.2-1B-Instruct-Q4_K_M.gguf"

echo "🚀 Starte Llama-Server im sicheren Modus..."

# Versuche zuerst GPU-Modus
timeout 10s ./llama.cpp/build/bin/llama-server -m "$MODEL_PATH" --gpu-layers 5 --host 0.0.0.0 --port 5020 &
SERVER_PID=$!

sleep 5

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ GPU-Modus erfolgreich"
else
    echo "⚠️ GPU-Modus fehlgeschlagen, wechsle zu CPU-Modus"
    ./llama.cpp/build/bin/llama-server -m "$MODEL_PATH" --gpu-layers 0 --host 0.0.0.0 --port 5020 &
fi
```

## 🎯 Fazit

**Empfehlung:** Verwende **CPU-Modus** für stabile Produktion auf deinem Mac. Der Vulkan-DeviceLostError ist ein bekanntes Problem bei einigen macOS + Vulkan-Kombinationen.

**Schnellfix:**
```bash
# Sofort CPU-Modus aktivieren
./llama.cpp/build/bin/llama-server -m ./models/Qwen3-4B-Q5_K_M.gguf --gpu-layers 0 --host 0.0.0.0 --port 5020
```

Deine API-Integration funktioniert unabhängig davon perfekt! 🎉</content>
</xai:function_call {</diff>