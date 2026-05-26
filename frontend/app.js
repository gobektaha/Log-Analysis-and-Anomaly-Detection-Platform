// ==========================================================================
// Küresel Durum (State) Yönetimi
// ==========================================================================
let renderedLogKeys = new Set();
let renderedAlertIds = new Set();
let anomalyChart = null;
let currentFilter = 'all'; // 'all' veya 'anomaly'
const API_BASE = '/api';

// ==========================================================================
// Sayfa Yüklendiğinde Başlatma
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initEventListeners();
    initChart();
    
    // Gerçek zamanlı polling döngüsünü başlat (Her 1 saniyede bir)
    fetchDashboardData();
    setInterval(fetchDashboardData, 1000);
});

// ==========================================================================
// Tema Yönetimi (Dark / Light Mode)
// ==========================================================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    } else {
        document.body.classList.remove('light-theme');
    }
    lucide.createIcons();
}

function toggleTheme() {
    const isLight = document.body.classList.toggle('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

// ==========================================================================
// Grafik İşlemleri (Chart.js)
// ==========================================================================
function initChart() {
    const ctx = document.getElementById('anomalyChart').getContext('2d');
    
    anomalyChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Brute Force', 'Scraping/Bot', 'Kritik Hata'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    '#f59e0b', // Amber / Warning
                    '#06b6d4', // Turkuaz / Info
                    '#ef4444'  // Kırmızı / Danger
                ],
                borderWidth: 1,
                borderColor: 'transparent'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: getComputedStyle(document.body).getPropertyValue('--text-primary').trim(),
                        font: {
                            family: 'Outfit',
                            size: 11
                        },
                        padding: 15
                    }
                }
            },
            cutout: '70%'
        }
    });
}

function updateChart(distribution) {
    const bruteForce = distribution["Brute Force"] || 0;
    const scraping = distribution["Scraping/Bot"] || 0;
    const critical = distribution["Kritik Hata (Checkout 500)"] || 0;
    const total = bruteForce + scraping + critical;

    const noDataMsg = document.getElementById('noChartDataMessage');
    const canvas = document.getElementById('anomalyChart');

    if (total === 0) {
        noDataMsg.style.display = 'flex';
        canvas.style.display = 'none';
    } else {
        noDataMsg.style.display = 'none';
        canvas.style.display = 'block';

        // Grafik verilerini güncelle
        anomalyChart.data.datasets[0].data = [bruteForce, scraping, critical];
        
        // Dinamik tema uyumluluğu için yazı rengini güncelle
        const textColor = getComputedStyle(document.body).getPropertyValue('--text-primary').trim();
        anomalyChart.options.plugins.legend.labels.color = textColor;
        
        anomalyChart.update();
    }
}

// ==========================================================================
// Veri Çekme ve Güncelleme İşlemleri (Polling)
// ==========================================================================
async function fetchDashboardData() {
    try {
        const [statsResponse, logsResponse, alertsResponse] = await Promise.all([
            fetch(`${API_BASE}/stats`),
            fetch(`${API_BASE}/logs?limit=100`),
            fetch(`${API_BASE}/alerts`)
        ]);

        if (statsResponse.ok && logsResponse.ok && alertsResponse.ok) {
            const stats = await statsResponse.json();
            const logs = await logsResponse.json();
            const alerts = await alertsResponse.json();

            updateStats(stats);
            updateLogsTable(logs);
            updateAlerts(alerts);
            updateChart(stats.distribution);
        }
    } catch (error) {
        console.error("Dashboard verileri alınırken hata oluştu:", error);
    }
}

// 1. İstatistik Kartları Güncellemesi
function updateStats(stats) {
    document.getElementById('valTotalRequests').textContent = stats.total_requests.toLocaleString();
    document.getElementById('valTotalAnomalies').textContent = stats.total_anomalies.toLocaleString();
    document.getElementById('valCriticalErrors').textContent = stats.critical_errors.toLocaleString();
    document.getElementById('valAnomalyRate').textContent = `${stats.anomaly_rate}%`;
}

// 2. Canlı Log Akışı Güncellemesi
function updateLogsTable(logs) {
    const tableBody = document.getElementById('logsTableBody');
    const emptyLogsState = document.getElementById('emptyLogsState');

    if (logs.length === 0) {
        emptyLogsState.style.display = 'flex';
        tableBody.parentElement.style.display = 'none';
        renderedLogKeys.clear();
        tableBody.innerHTML = '';
        return;
    }

    emptyLogsState.style.display = 'none';
    tableBody.parentElement.style.display = 'table';

    // Yeni gelen logları tersten döngüye sokup ekliyoruz (kronolojik sırayla tablo üstüne gelsin diye)
    // backend en yeni logu dizinin en başına koyduğu için, diziyi ters çevirip işliyoruz
    const reversedLogs = [...logs].reverse();

    reversedLogs.forEach(log => {
        const logKey = `${log.timestamp}|${log.ip_address}|${log.endpoint}|${log.status_code}`;
        
        if (!renderedLogKeys.has(logKey)) {
            renderedLogKeys.add(logKey);
            
            const tr = document.createElement('tr');
            tr.className = 'new-row';
            
            // Anomali ise renklendir
            if (log.is_anomaly) {
                tr.classList.add('anomaly-row');
                if (log.anomaly_severity === 'medium') tr.classList.add('medium');
                else if (log.anomaly_severity === 'high') tr.classList.add('high');
                else if (log.anomaly_severity === 'critical') tr.classList.add('critical');
            }

            // Zaman formatı (HH:MM:SS.mmm)
            const timeStr = new Date(log.timestamp).toLocaleTimeString('tr-TR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }) + '.' + new Date(log.timestamp).getMilliseconds().toString().padStart(3, '0');

            // Durum kodu sınıfı
            let statusClass = 'status-2xx';
            if (log.status_code >= 400 && log.status_code < 500) statusClass = 'status-4xx';
            else if (log.status_code >= 500) statusClass = 'status-5xx';

            // Güvenlik durumu rozeti
            let statusBadge = `<span class="badge badge-green">Temiz</span>`;
            if (log.is_anomaly) {
                if (log.anomaly_severity === 'medium') {
                    statusBadge = `<span class="badge badge-info"><i data-lucide="bot" style="width:10px; height:10px; margin-right:3px;"></i> Bot</span>`;
                } else if (log.anomaly_severity === 'high') {
                    statusBadge = `<span class="badge badge-orange"><i data-lucide="key-round" style="width:10px; height:10px; margin-right:3px;"></i> BruteForce</span>`;
                } else if (log.anomaly_severity === 'critical') {
                    statusBadge = `<span class="badge badge-red"><i data-lucide="skull" style="width:10px; height:10px; margin-right:3px;"></i> Tehdit</span>`;
                }
            }

            tr.innerHTML = `
                <td>${timeStr}</td>
                <td class="log-ip">${log.ip_address}</td>
                <td><span class="log-method">${log.method}</span></td>
                <td class="log-endpoint">${log.endpoint}</td>
                <td><span class="log-status ${statusClass}">${log.status_code}</span></td>
                <td>${statusBadge}</td>
            `;

            // En üste ekle (prepend)
            tableBody.insertBefore(tr, tableBody.firstChild);
            
            // Eğer aktif filtre 'anomaly' ise ve bu normal logsa gizle
            if (currentFilter === 'anomaly' && !log.is_anomaly) {
                tr.style.display = 'none';
            }

            // Mikro animasyon süresi bittiğinde sınıfı temizle
            setTimeout(() => {
                tr.classList.remove('new-row');
            }, 500);
        }
    });

    // Lucide ikonlarını yeniden oluştur
    lucide.createIcons();

    // Tabloda çok fazla log birikmesini önle (max 100 satır)
    while (tableBody.children.length > 100) {
        const lastChild = tableBody.lastChild;
        // renderedLogKeys setinden de silelim
        // Satırdaki verileri kullanarak key'i yeniden oluşturalım
        // Bu prototip için en basiti listeyi sınırlamak
        tableBody.removeChild(lastChild);
    }
}

// 3. Güvenlik Alarmları Güncellemesi
function updateAlerts(alerts) {
    const alertsContainer = document.getElementById('alertsContainer');
    const emptyAlertsState = document.getElementById('emptyAlertsState');
    const alertCountBadge = document.getElementById('alertCountBadge');

    alertCountBadge.textContent = alerts.length;

    if (alerts.length === 0) {
        emptyAlertsState.style.display = 'flex';
        // Mevcut alarmları sil
        document.querySelectorAll('.alert-item').forEach(el => el.remove());
        renderedAlertIds.clear();
        return;
    }

    emptyAlertsState.style.display = 'none';

    // Yeni alarmları en üste (başa) ekle
    alerts.forEach(alert => {
        if (!renderedAlertIds.has(alert.id)) {
            renderedAlertIds.add(alert.id);

            const alertDiv = document.createElement('div');
            alertDiv.className = `alert-item ${alert.severity}`;
            alertDiv.id = `alert-${alert.id}`;

            const timeStr = new Date(alert.timestamp).toLocaleTimeString('tr-TR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            // Tetikleyici logları güzel bir JSON formatına getir
            const triggerLogsFormatted = alert.triggering_logs.map(l => 
                `[${new Date(l.timestamp).toLocaleTimeString('tr-TR')}] ${l.ip_address} -> ${l.method} ${l.endpoint} (${l.status_code})`
            ).join('\n');

            alertDiv.innerHTML = `
                <div class="alert-header">
                    <span class="alert-title">
                        <i data-lucide="${getAlertIcon(alert.type)}"></i> ${alert.type}
                    </span>
                    <span class="alert-time">${timeStr}</span>
                </div>
                <div class="alert-body">
                    ${alert.details}
                </div>
                <div class="alert-footer">
                    <span>IP: <span class="alert-ip">${alert.ip_address}</span></span>
                    <span class="alert-severity-badge">${alert.severity === 'critical' ? 'Kritik' : alert.severity === 'high' ? 'Yüksek' : 'Orta'}</span>
                </div>
                <button class="alert-details-toggle" onclick="toggleAlertDetails('${alert.id}')">
                    <i data-lucide="terminal" style="width:11px; height:11px;"></i> Tetikleyici Logları Göster/Gizle
                </button>
                <pre class="alert-triggering-logs" id="logs-${alert.id}">${triggerLogsFormatted}</pre>
            `;

            // AlertsContainer'ın en üstüne ekle (boş durum elamanından hemen sonra)
            alertsContainer.insertBefore(alertDiv, alertsContainer.firstChild);
        }
    });

    lucide.createIcons();
}

function getAlertIcon(type) {
    if (type.includes("Brute Force")) return "key-round";
    if (type.includes("Scraping")) return "bot";
    return "skull";
}

// Alarm detaylarını aç/kapat
window.toggleAlertDetails = function(alertId) {
    const logsPre = document.getElementById(`logs-${alertId}`);
    logsPre.classList.toggle('open');
};

// ==========================================================================
// Olay Dinleyicileri (Event Listeners)
// ==========================================================================
function initEventListeners() {
    // 1. Tema Geçiş Butonu
    document.getElementById('themeToggleBtn').addEventListener('click', toggleTheme);

    // 2. Sistemi Temizleme
    document.getElementById('clearDataBtn').addEventListener('click', clearAllData);

    // 5. Log Filtreleme Butonları
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            currentFilter = e.currentTarget.getAttribute('data-filter');
            applyLogFilter();
        });
    });
}

// Simülasyon API Çağrısı
async function triggerScenario(scenario) {
    try {
        const response = await fetch(`${API_BASE}/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario })
        });
        if (!response.ok) {
            console.error("Senaryo tetiklenirken hata oluştu.");
        }
    } catch (e) {
        console.error("Ağ hatası:", e);
    }
}

// Verileri Temizleme API Çağrısı
async function clearAllData() {
    if (confirm("Tüm log akışını, alarmları ve istatistikleri sıfırlamak istediğinize emin misiniz?")) {
        try {
            const response = await fetch(`${API_BASE}/clear`, { method: 'POST' });
            if (response.ok) {
                // UI Sıfırla
                renderedLogKeys.clear();
                renderedAlertIds.clear();
                
                document.getElementById('logsTableBody').innerHTML = '';
                document.getElementById('emptyLogsState').style.display = 'flex';
                document.getElementById('logsTableBody').parentElement.style.display = 'none';

                document.querySelectorAll('.alert-item').forEach(el => el.remove());
                document.getElementById('emptyAlertsState').style.display = 'flex';
                document.getElementById('alertCountBadge').textContent = '0';

                updateStats({ total_requests: 0, total_anomalies: 0, critical_errors: 0, anomaly_rate: 0.0 });
                updateChart({ "Brute Force": 0, "Scraping/Bot": 0, "Kritik Hata (Checkout 500)": 0 });
            }
        } catch (e) {
            console.error("Veriler temizlenirken hata oluştu:", e);
        }
    }
}

// Log Filtresini Uygula (HTML satırlarını gizle/göster)
function applyLogFilter() {
    const rows = document.querySelectorAll('#logsTableBody tr');
    rows.forEach(row => {
        if (currentFilter === 'all') {
            row.style.display = '';
        } else if (currentFilter === 'anomaly') {
            if (row.classList.contains('anomaly-row')) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}
