/**
 * Real-time Analytics Dashboard
 * Advanced fraud detection analytics with live updates and visualizations
 */

class RealTimeAnalytics {
    constructor() {
        this.updateInterval = 5000; // 5 seconds
        this.charts = {};
        this.isActive = true;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.startRealTimeUpdates();
        this.setupMobileOptimizations();
    }

    setupEventListeners() {
        // Auto-refresh toggle
        const refreshToggle = document.getElementById('auto-refresh-toggle');
        if (refreshToggle) {
            refreshToggle.addEventListener('change', (e) => {
                this.isActive = e.target.checked;
                if (this.isActive) {
                    this.startRealTimeUpdates();
                } else {
                    this.stopRealTimeUpdates();
                }
            });
        }

        // Refresh rate selector
        const refreshRate = document.getElementById('refresh-rate');
        if (refreshRate) {
            refreshRate.addEventListener('change', (e) => {
                this.updateInterval = parseInt(e.target.value) * 1000;
                if (this.isActive) {
                    this.stopRealTimeUpdates();
                    this.startRealTimeUpdates();
                }
            });
        }

        // Mobile menu toggle
        const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
        if (mobileMenuToggle) {
            mobileMenuToggle.addEventListener('click', () => {
                this.toggleMobileMenu();
            });
        }
    }

    initializeCharts() {
        this.initFraudTrendChart();
        this.initRiskDistributionChart();
        this.initGeographicChart();
        this.initRealTimeMetrics();
    }

    initFraudTrendChart() {
        const ctx = document.getElementById('fraudTrendChart');
        if (!ctx) return;

        this.charts.fraudTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Fraud Detections',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Total Transactions',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e2e8f0'
                        }
                    },
                    title: {
                        display: true,
                        text: '🔍 Real-Time Fraud Detection Trends',
                        color: '#00d4ff',
                        font: { size: 16, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#a0aec0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    },
                    y: {
                        ticks: { color: '#a0aec0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    initRiskDistributionChart() {
        const ctx = document.getElementById('riskDistributionChart');
        if (!ctx) return;

        this.charts.riskDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Very Low', 'Low', 'Medium', 'High', 'Very High'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        '#00d4ff',
                        '#00ff88',
                        '#ffcd3c',
                        '#ff6b35',
                        '#ff3e3e'
                    ],
                    borderColor: '#1a202c',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#e2e8f0',
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    title: {
                        display: true,
                        text: '⚠️ Risk Level Distribution',
                        color: '#00d4ff',
                        font: { size: 16, weight: 'bold' }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
    }

    initGeographicChart() {
        const ctx = document.getElementById('geographicChart');
        if (!ctx) return;

        this.charts.geographic = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['North America', 'Europe', 'Asia Pacific', 'Latin America', 'Middle East & Africa'],
                datasets: [{
                    label: 'Fraud Incidents',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderColor: '#ef4444',
                    borderWidth: 1
                }, {
                    label: 'Total Transactions',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: '#3b82f6',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e2e8f0'
                        }
                    },
                    title: {
                        display: true,
                        text: '🌍 Geographic Risk Distribution',
                        color: '#00d4ff',
                        font: { size: 16, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#a0aec0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    },
                    y: {
                        ticks: { color: '#a0aec0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                }
            }
        });
    }

    initRealTimeMetrics() {
        // Initialize real-time metric displays
        this.updateMetricDisplay('total-transactions', 0);
        this.updateMetricDisplay('fraud-detected', 0);
        this.updateMetricDisplay('fraud-rate', 0);
        this.updateMetricDisplay('avg-confidence', 0);
    }

    startRealTimeUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }

        this.updateTimer = setInterval(() => {
            if (this.isActive) {
                this.fetchAndUpdateData();
            }
        }, this.updateInterval);

        // Initial update
        this.fetchAndUpdateData();
    }

    stopRealTimeUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }

    async fetchAndUpdateData() {
        try {
            const [statsResponse, recentResponse] = await Promise.all([
                fetch('/api/stats'),
                fetch('/api/transactions/recent?limit=20')
            ]);

            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                this.updateDashboardMetrics(stats);
            }

            if (recentResponse.ok) {
                const recentData = await recentResponse.json();
                this.updateCharts(recentData);
            }

            this.updateLastRefresh();
        } catch (error) {
            console.error('Error fetching real-time data:', error);
            this.showConnectionError();
        }
    }

    updateDashboardMetrics(stats) {
        if (stats.message) return; // No data available

        this.updateMetricDisplay('total-transactions', stats.total_predictions);
        this.updateMetricDisplay('fraud-detected', stats.fraud_predictions);
        this.updateMetricDisplay('fraud-rate', (stats.fraud_rate * 100).toFixed(1));
        this.updateMetricDisplay('avg-confidence', (stats.avg_confidence * 100).toFixed(1));

        // Update progress bars
        this.updateProgressBar('fraud-rate-bar', stats.fraud_rate * 100);
        this.updateProgressBar('confidence-bar', stats.avg_confidence * 100);
    }

    updateMetricDisplay(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const numValue = typeof value === 'number' ? value : parseFloat(value) || 0;
            element.textContent = numValue.toLocaleString();

            // Add animation effect
            element.style.transform = 'scale(1.1)';
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 200);
        }
    }

    updateProgressBar(elementId, percentage) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.width = `${Math.min(percentage, 100)}%`;
        }
    }

    updateCharts(recentData) {
        if (!recentData || !recentData.predictions) return;

        // Update fraud trend chart
        this.updateFraudTrendChart(recentData.predictions);

        // Update risk distribution
        this.updateRiskDistributionChart(recentData.predictions);

        // Update geographic chart (simulated data)
        this.updateGeographicChart();
    }

    updateFraudTrendChart(predictions) {
        if (!this.charts.fraudTrend) return;

        // Group predictions by hour
        const hourlyData = this.groupPredictionsByHour(predictions);

        this.charts.fraudTrend.data.labels = hourlyData.labels;
        this.charts.fraudTrend.data.datasets[0].data = hourlyData.fraudCounts;
        this.charts.fraudTrend.data.datasets[1].data = hourlyData.totalCounts;

        this.charts.fraudTrend.update('active');
    }

    updateRiskDistributionChart(predictions) {
        if (!this.charts.riskDistribution) return;

        const riskCounts = {
            'Very Low': 0,
            'Low': 0,
            'Medium': 0,
            'High': 0,
            'Very High': 0
        };

        predictions.forEach(pred => {
            const riskLevel = pred.risk_level || 'Unknown';
            if (riskCounts.hasOwnProperty(riskLevel)) {
                riskCounts[riskLevel]++;
            }
        });

        this.charts.riskDistribution.data.datasets[0].data = Object.values(riskCounts);
        this.charts.riskDistribution.update('active');
    }

    updateGeographicChart() {
        if (!this.charts.geographic) return;

        // Simulate geographic data
        const regions = ['North America', 'Europe', 'Asia Pacific', 'Latin America', 'Middle East & Africa'];
        const fraudData = regions.map(() => Math.floor(Math.random() * 50));
        const totalData = regions.map(() => Math.floor(Math.random() * 500) + 100);

        this.charts.geographic.data.datasets[0].data = fraudData;
        this.charts.geographic.data.datasets[1].data = totalData;
        this.charts.geographic.update('active');
    }

    groupPredictionsByHour(predictions) {
        const hourlyGroups = {};
        const now = new Date();

        // Initialize last 24 hours
        for (let i = 23; i >= 0; i--) {
            const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
            const key = hour.getHours().toString().padStart(2, '0') + ':00';
            hourlyGroups[key] = { fraud: 0, total: 0 };
        }

        // Group predictions
        predictions.forEach(pred => {
            const predDate = new Date(pred.timestamp);
            const hourKey = predDate.getHours().toString().padStart(2, '0') + ':00';

            if (hourlyGroups[hourKey]) {
                hourlyGroups[hourKey].total++;
                if (pred.prediction === 1) {
                    hourlyGroups[hourKey].fraud++;
                }
            }
        });

        return {
            labels: Object.keys(hourlyGroups),
            fraudCounts: Object.values(hourlyGroups).map(g => g.fraud),
            totalCounts: Object.values(hourlyGroups).map(g => g.total)
        };
    }

    updateLastRefresh() {
        const element = document.getElementById('last-refresh');
        if (element) {
            element.textContent = new Date().toLocaleTimeString();
        }
    }

    showConnectionError() {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.innerHTML = '<span class="error">⚠️ Connection Error</span>';
            setTimeout(() => {
                statusElement.innerHTML = '<span class="success">🟢 Connected</span>';
            }, 3000);
        }
    }

    setupMobileOptimizations() {
        // Add touch gestures for mobile
        let startY = 0;
        let currentY = 0;
        let isScrolling = false;

        document.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
        });

        document.addEventListener('touchmove', (e) => {
            currentY = e.touches[0].clientY;
            isScrolling = true;
        });

        document.addEventListener('touchend', () => {
            if (isScrolling && startY - currentY > 50) {
                // Swipe up - refresh data
                this.fetchAndUpdateData();
            }
            isScrolling = false;
        });

        // Responsive chart resizing
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => {
                if (chart) chart.resize();
            });
        });
    }

    toggleMobileMenu() {
        const mobileMenu = document.getElementById('mobile-menu');
        const overlay = document.getElementById('mobile-overlay');

        if (mobileMenu && overlay) {
            mobileMenu.classList.toggle('active');
            overlay.classList.toggle('active');
        }
    }

    // 3D Visualization Methods
    init3DRiskVisualization() {
        // Initialize 3D risk visualization using Three.js
        const container = document.getElementById('3d-risk-container');
        if (!container) return;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setClearColor(0x000000, 0);
        container.appendChild(renderer.domElement);

        // Create 3D risk spheres
        this.create3DRiskSpheres(scene);

        camera.position.z = 5;

        // Animation loop
        const animate = () => {
            requestAnimationFrame(animate);
            scene.rotation.y += 0.01;
            renderer.render(scene, camera);
        };

        animate();
    }

    create3DRiskSpheres(scene) {
        const riskLevels = [
            { name: 'Low', color: 0x00ff88, size: 0.3 },
            { name: 'Medium', color: 0xffcd3c, size: 0.5 },
            { name: 'High', color: 0xff6b35, size: 0.7 },
            { name: 'Very High', color: 0xff3e3e, size: 1.0 }
        ];

        riskLevels.forEach((risk, index) => {
            const geometry = new THREE.SphereGeometry(risk.size, 32, 32);
            const material = new THREE.MeshBasicMaterial({
                color: risk.color,
                transparent: true,
                opacity: 0.8
            });

            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.x = (index - 1.5) * 2;
            scene.add(sphere);
        });
    }

    // Network Graph Visualization
    initNetworkGraph() {
        const container = document.getElementById('network-graph-container');
        if (!container) return;

        // Initialize network graph using D3.js
        const width = container.clientWidth;
        const height = container.clientHeight;

        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Create sample network data
        const nodes = [
            { id: 'bank', group: 1, size: 20 },
            { id: 'customer1', group: 2, size: 10 },
            { id: 'customer2', group: 2, size: 10 },
            { id: 'merchant1', group: 3, size: 15 },
            { id: 'merchant2', group: 3, size: 15 },
            { id: 'fraud_node', group: 4, size: 25 }
        ];

        const links = [
            { source: 'bank', target: 'customer1', value: 1 },
            { source: 'bank', target: 'customer2', value: 1 },
            { source: 'customer1', target: 'merchant1', value: 2 },
            { source: 'customer2', target: 'merchant2', value: 2 },
            { source: 'fraud_node', target: 'customer1', value: 3 },
            { source: 'fraud_node', target: 'merchant1', value: 3 }
        ];

        this.drawNetworkGraph(svg, nodes, links, width, height);
    }

    drawNetworkGraph(svg, nodes, links, width, height) {
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2));

        const link = svg.append('g')
            .selectAll('line')
            .data(links)
            .enter().append('line')
            .attr('stroke-width', d => Math.sqrt(d.value))
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6);

        const node = svg.append('g')
            .selectAll('circle')
            .data(nodes)
            .enter().append('circle')
            .attr('r', d => d.size)
            .attr('fill', d => {
                const colors = ['#69b3a2', '#404080', '#f95959', '#ff6b35'];
                return colors[d.group - 1];
            })
            .call(d3.drag()
                .on('start', this.dragstarted)
                .on('drag', this.dragged)
                .on('end', this.dragended));

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
        });
    }

    dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.realTimeAnalytics = new RealTimeAnalytics();
});

// Progressive Web App Support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}