#!/bin/bash
# Optimiertes Start-Skript für llama.cpp mit Streaming-Unterstützung

MODEL_PATH="./models/Qwen3-4B-Q5_K_M.gguf"
BACKUP_MODEL="./models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

echo "🚀 Starte llama-server mit Streaming-Optimierungen..."
echo "Model: $(basename $MODEL_PATH)"
echo "Port: 5020"
echo ""

# Prüfe ob Modell existiert
if [ ! -f "$MODEL_PATH" ]; then
    echo "⚠️  Hauptmodell nicht gefunden: $MODEL_PATH"
    if [ -f "$BACKUP_MODEL" ]; then
        echo "✅ Verwende Backup-Modell: $(basename $BACKUP_MODEL)"
        MODEL_PATH="$BACKUP_MODEL"
    else
        echo "❌ Kein Modell gefunden! Bitte Modelle herunterladen."
        exit 1
    fi
fi

# CPU-Kerne ermitteln für optimale Thread-Konfiguration
CPU_CORES=$(sysctl -n hw.ncpu)
THREADS=$((CPU_CORES - 2))  # 2 Kerne für System reservieren
if [ $THREADS -lt 4 ]; then
    THREADS=4
fi

echo "🔧 System-Informationen:"
echo "   CPU-Kerne: $CPU_CORES"
echo "   Threads für LLM: $THREADS"
echo "   Parallel Slots: 4"
echo "   HTTP-Threads: 4"
echo ""

# Starte llama-server mit Streaming-Optimierungen
./llama.cpp/build/bin/llama-server \
  -m "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port 5020 \
  --ctx-size 2048 \
  --threads $THREADS \
  --gpu-layers 0 \
  --cont-batching \
  --parallel 4 \
  --threads-http 4 \
  --timeout 300 \
  --log-format json \
  --log-disable \
  --metrics

echo ""
echo "✅ llama-server gestartet mit folgenden Features:"
echo "   • Streaming über Server-Sent Events (SSE)"
echo "   • Kontinuierliches Batching (--cont-batching)"
echo "   • 4 parallele Anfragen (--parallel 4)"
echo "   • 5 Minuten Timeout für lange Sessions"
echo "   • JSON-Logging für Monitoring"
echo ""
echo "📡 API-Endpunkte:"
echo "   • Chat Completions: http://localhost:5020/v1/chat/completions"
echo "   • Completions:      http://localhost:5020/v1/completions"
echo "   • Health Check:     http://localhost:5020/health"
echo ""
echo "🔍 Streaming aktivieren mit: \"stream\": true in API-Requests"
echo "📊 Monitoring: tail -f logs/llama_server.log"
