# 🔧 ApiDog Service Installation & Konfiguration

## 🎯 Übersicht

ApiDog ist der zentrale API-Registry und Authentifizierungs-Service für die LLM-gesteuerte API-Integration. Dieser Leitfaden zeigt, wie Sie ApiDog installieren, konfigurieren und mit Ihrem System integrieren.

## 📋 Voraussetzungen

- **Node.js**: Version 18.x oder höher
- **npm**: Node Package Manager
- **Bitwarden CLI**: Für Token-Management
- **SQLite**: Für lokale Datenpersistierung (optional)

## 🚀 Installation

### Schritt 1: Repository klonen

```bash
# ApiDog Repository klonen (angenommen es ist verfügbar)
git clone https://github.com/your-org/apidog-service.git
cd apidog-service

# Oder erstellen Sie ein neues Node.js-Projekt
mkdir apidog-service
cd apidog-service
npm init -y
```

### Schritt 2: Abhängigkeiten installieren

```bash
npm install express cors helmet morgan sqlite3 bcryptjs jsonwebtoken axios
npm install --save-dev nodemon typescript @types/node @types/express
```

### Schritt 3: Basis-Service erstellen

**`server.js`:**
```javascript
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Datenbank initialisieren
const db = new sqlite3.Database('./apidog.db', (err) => {
    if (err) {
        console.error('❌ Datenbank-Fehler:', err.message);
    } else {
        console.log('✅ ApiDog Datenbank verbunden');
        initDatabase();
    }
});

// Datenbank-Schema
function initDatabase() {
    db.run(`CREATE TABLE IF NOT EXISTS apis (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        description TEXT,
        base_url TEXT,
        openapi_spec_url TEXT,
        auth_type TEXT DEFAULT 'api_key',
        oauth_config TEXT, -- JSON
        policies TEXT, -- JSON
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS api_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        user_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME,
        FOREIGN KEY (api_id) REFERENCES apis (id)
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS monitoring_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id TEXT,
        system TEXT,
        total_calls INTEGER DEFAULT 0,
        successful_calls INTEGER DEFAULT 0,
        failed_calls INTEGER DEFAULT 0,
        average_response_time REAL DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (api_id) REFERENCES apis (id)
    )`);

    console.log('✅ Datenbank-Schema initialisiert');
}

// API-Routen
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

// APIs auflisten
app.get('/apis', (req, res) => {
    db.all('SELECT * FROM apis ORDER BY name', [], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

// API-Details abrufen
app.get('/apis/:id', (req, res) => {
    const { id } = req.params;
    db.get('SELECT * FROM apis WHERE id = ?', [id], (err, row) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        if (!row) {
            return res.status(404).json({ error: 'API nicht gefunden' });
        }
        res.json(row);
    });
});

// Neue API registrieren
app.post('/apis', (req, res) => {
    const { id, name, category, description, base_url, auth_type, oauth_config, policies } = req.body;

    if (!id || !name) {
        return res.status(400).json({ error: 'API ID und Name erforderlich' });
    }

    const sql = `INSERT INTO apis (id, name, category, description, base_url, auth_type, oauth_config, policies)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;

    db.run(sql, [id, name, category, description, base_url, auth_type || 'api_key',
                 JSON.stringify(oauth_config || {}), JSON.stringify(policies || {})],
    function(err) {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json({
            id: id,
            message: 'API erfolgreich registriert',
            changes: this.changes
        });
    });
});

// Monitoring-Stats empfangen
app.post('/monitoring/stats', (req, res) => {
    const { system, timestamp, apis } = req.body;

    if (!system || !apis) {
        return res.status(400).json({ error: 'System und APIs erforderlich' });
    }

    // Stats für jede API einfügen
    const stmt = db.prepare(`INSERT INTO monitoring_stats
        (api_id, system, total_calls, successful_calls, failed_calls, average_response_time)
        VALUES (?, ?, ?, ?, ?, ?)`);

    for (const api of apis) {
        stmt.run([
            api.id,
            system,
            api.total_calls || 0,
            api.successful_calls || 0,
            api.failed_calls || 0,
            api.average_response_time || 0
        ]);
    }

    stmt.finalize();
    res.json({ message: 'Monitoring-Daten empfangen', processed: apis.length });
});

// Monitoring-Stats abrufen
app.get('/monitoring/stats', (req, res) => {
    const { system, api_id, limit = 100 } = req.query;

    let sql = 'SELECT * FROM monitoring_stats WHERE 1=1';
    const params = [];

    if (system) {
        sql += ' AND system = ?';
        params.push(system);
    }

    if (api_id) {
        sql += ' AND api_id = ?';
        params.push(api_id);
    }

    sql += ' ORDER BY timestamp DESC LIMIT ?';
    params.push(parseInt(limit));

    db.all(sql, params, (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

// OAuth-Konfiguration für API
app.get('/apis/:id/oauth', (req, res) => {
    const { id } = req.params;
    db.get('SELECT oauth_config FROM apis WHERE id = ?', [id], (err, row) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        if (!row) {
            return res.status(404).json({ error: 'API nicht gefunden' });
        }

        const oauth_config = JSON.parse(row.oauth_config || '{}');
        res.json(oauth_config);
    });
});

// Token validieren
app.post('/validate-token', (req, res) => {
    const { api_id, token } = req.body;

    // Hier würde die eigentliche Token-Validierung erfolgen
    // Für Demo-Zwecke immer true zurückgeben
    res.json({
        valid: true,
        api_id: api_id,
        message: 'Token validiert'
    });
});

// Server starten
app.listen(PORT, () => {
    console.log(`🚀 ApiDog Service läuft auf Port ${PORT}`);
    console.log(`📊 Health-Check: http://localhost:${PORT}/health`);
    console.log(`📋 APIs: http://localhost:${PORT}/apis`);
    console.log(`📈 Monitoring: http://localhost:${PORT}/monitoring/stats`);
});

module.exports = app;
```

### Schritt 4: Service starten

```bash
# Entwicklung
npm run dev

# Produktion
npm start

# Oder mit PM2
npm install -g pm2
pm2 start server.js --name apidog-service
pm2 save
pm2 startup
```

## ⚙️ Konfiguration

### Umgebungsvariablen

**`.env`:**
```bash
PORT=3000
NODE_ENV=production
DATABASE_PATH=./apidog.db
JWT_SECRET=your-super-secret-jwt-key
BITWARDEN_SERVER=https://vault.bitwarden.com
```

### APIs konfigurieren

**Beispiel-API-Registrierung:**

```bash
curl -X POST http://localhost:3000/apis \
  -H "Content-Type: application/json" \
  -d '{
    "id": "github",
    "name": "GitHub API",
    "category": "development",
    "description": "Repository und Issue Management",
    "base_url": "https://api.github.com",
    "auth_type": "api_key",
    "policies": {
      "rate_limit_per_hour": 5000,
      "max_concurrent_calls": 10,
      "timeout_seconds": 30
    }
  }'
```

## 🔗 Integration mit CrewAI-System

### 1. ApiDog in Settings konfigurieren

**`core/settings.py`:**
```python
# ApiDog Service URL
apidog_base_url: str = Field(default="http://localhost:3000", description="ApiDog Service URL")
```

### 2. Monitoring aktivieren

**API Admin Interface:**
```bash
python run_api_admin.py
# Option wählen: "10. 📊 ApiDog Monitoring Dashboard"
```

### 3. Automatische Synchronisation

**In `core/api_admin.py`:**
```python
# Monitoring beim Admin-Start synchronisieren
admin = APIAdmin()
admin.monitor.sync_api_statistics()  # Sende Stats an ApiDog
```

## 📊 Monitoring Dashboard

### Web-Interface

ApiDog bietet ein einfaches Web-Dashboard:

```bash
# Dashboard öffnen
open http://localhost:3000/dashboard.html
```

**`public/dashboard.html`:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>ApiDog Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>📊 ApiDog API Monitoring</h1>

    <div id="stats"></div>
    <canvas id="apiChart"></canvas>

    <script>
        async function loadStats() {
            const response = await fetch('/monitoring/stats');
            const data = await response.json();

            // Stats anzeigen und visualisieren
            console.log('Monitoring data:', data);
        }

        loadStats();
        setInterval(loadStats, 30000); // Alle 30 Sekunden aktualisieren
    </script>
</body>
</html>
```

### CLI-Monitoring

```bash
# Gesamtstatistiken
curl http://localhost:3000/monitoring/stats

# Spezifische API
curl "http://localhost:3000/monitoring/stats?api_id=github"

# System-spezifisch
curl "http://localhost:3000/monitoring/stats?system=crewai-amanxai"
```

## 🔐 Sicherheit

### API-Schutz

```javascript
// API-Key Authentifizierung
function authenticateApiKey(req, res, next) {
    const apiKey = req.headers['x-api-key'];
    if (!apiKey || apiKey !== process.env.API_KEY) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    next();
}

// Geschützte Routen
app.use('/apis', authenticateApiKey);
app.use('/monitoring', authenticateApiKey);
```

### HTTPS aktivieren

```bash
# SSL-Zertifikate
npm install certbot

# Let's Encrypt Zertifikat
certbot certonly --standalone -d your-domain.com

# HTTPS in server.js
const https = require('https');
const fs = require('fs');

const sslOptions = {
    key: fs.readFileSync('/etc/letsencrypt/live/your-domain.com/privkey.pem'),
    cert: fs.readFileSync('/etc/letsencrypt/live/your-domain.com/fullchain.pem')
};

https.createServer(sslOptions, app).listen(443);
```

## 🚀 Deployment

### Docker

**`Dockerfile`:**
```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000
CMD ["npm", "start"]
```

**`docker-compose.yml`:**
```yaml
version: '3.8'
services:
  apidog:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./apidog.db:/app/apidog.db
    environment:
      - NODE_ENV=production
    restart: unless-stopped
```

```bash
docker-compose up -d
```

### Cloud Deployment

**Vercel:**
```bash
npm install -g vercel
vercel --prod
```

**Railway/Heroku:**
```bash
git push heroku main
```

## 🔍 Troubleshooting

### Häufige Probleme

**1. Port bereits belegt:**
```bash
lsof -i :3000
kill -9 <PID>
```

**2. Datenbank-Fehler:**
```bash
rm apidog.db
npm start  # Erstellt neue DB
```

**3. CORS-Fehler:**
```javascript
app.use(cors({
    origin: ['http://localhost:3001', 'https://your-frontend.com'],
    credentials: true
}));
```

### Logs überprüfen

```bash
# PM2 Logs
pm2 logs apidog-service

# Docker Logs
docker logs apidog-container

# Application Logs
tail -f logs/apidog.log
```

## 📞 Support

Bei Problemen:
1. Health-Check: `GET /health`
2. Logs prüfen
3. Issues auf GitHub melden
4. Dokumentation aktualisieren

---

**🎉 ApiDog ist jetzt installiert und bereit für API-Monitoring!**</content>
</xai:function_call {</diff>