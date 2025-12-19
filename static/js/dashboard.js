// static/js/dashboard.js

let stockChart = null;
let categoryChart = null;

/**
 * Initialize Stock Movement Chart
 */
function initStockChart(data) {
    const ctx = document.getElementById('stockChart');
    if (!ctx) return;
    
    stockChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.months,
            datasets: [
                {
                    label: 'Stock In',
                    data: data.stockIn,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Stock Out',
                    data: data.stockOut,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize Category Distribution Chart
 */
function initCategoryChart(data) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    
    const colors = [
        '#007bff', '#28a745', '#dc3545', '#ffc107', 
        '#17a2b8', '#6c757d', '#343a40', '#fd7e14'
    ];
    
    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.categoryNames,
            datasets: [{
                data: data.categoryCounts,
                backgroundColor: colors.slice(0, data.categoryNames.length),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Resize Chart
 */
function resizeChart(chartId, size) {
    const container = document.getElementById(chartId + 'Container');
    if (!container) return;
    
    // Remove all size classes
    container.classList.remove('size-small', 'size-medium', 'size-large');
    
    // Add new size class
    container.classList.add('size-' + size);
    
    // Update chart
    const chart = (chartId === 'stockChart') ? stockChart : categoryChart;
    if (chart) {
        setTimeout(() => {
            chart.resize();
        }, 300);
    }
}

/**
 * Save Chart as Image
 */
function saveChartImage(chartId) {
    const chart = (chartId === 'stockChart') ? stockChart : categoryChart;
    if (!chart) return;
    
    const url = chart.toBase64Image();
    const link = document.createElement('a');
    link.download = chartId + '_' + new Date().getTime() + '.png';
    link.href = url;
    link.click();
}

/**
 * Refresh Dashboard Stats (Real-time)
 */
function refreshDashboardStats() {
    fetch('/api/dashboard-stats')
        .then(response => response.json())
        .then(data => {
            // Update stats if elements exist
            const updateStat = (selector, value) => {
                const element = document.querySelector(selector);
                if (element) {
                    element.textContent = value;
                    element.classList.add('animate-update');
                    setTimeout(() => element.classList.remove('animate-update'), 500);
                }
            };
            
            // Update each stat - adjust selectors to match your HTML
            // This is an example, adjust based on your actual HTML structure
        })
        .catch(error => console.error('Error refreshing stats:', error));
}

/**
 * Auto-refresh every 30 seconds
 */
setInterval(refreshDashboardStats, 30000);

/**
 * Product Quick Search (Autocomplete)
 */
function initProductSearch() {
    const searchInput = document.querySelector('input[name="q"]');
    if (!searchInput) return;
    
    let timeout = null;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(timeout);
        
        const query = this.value.trim();
        if (query.length < 2) return;
        
        timeout = setTimeout(() => {
            fetch(`/api/products/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    // Show autocomplete dropdown
                    // Implementation depends on your UI framework
                    console.log('Search results:', data);
                })
                .catch(error => console.error('Search error:', error));
        }, 300);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initProductSearch();
    
    // Add animation class for stats
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
});