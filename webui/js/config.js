const CONFIG = {
    // API endpoints
    API_BASE_URL: 'http://localhost:8000/api',
    ENDPOINTS: {
        SENSORS: '/sensors',
        MEASUREMENTS: '/measurements',
        RECENT: '/measurements/recent',
        STATS: '/measurements/{sensor_id}/stats',
        TREND: '/measurements/{sensor_id}/trend'
    },

    // Chart.js configuration
    CHART_OPTIONS: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false
        },
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    padding: 20,
                    usePointStyle: true,
                    pointStyle: 'circle'
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                padding: 12,
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                titleColor: '#000',
                titleFont: {
                    size: 14,
                    weight: 'bold'
                },
                bodyColor: '#666',
                bodyFont: {
                    size: 13
                },
                borderColor: '#ddd',
                borderWidth: 1,
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            switch(context.dataset.yAxisID) {
                                case 'temperature':
                                    label += context.parsed.y.toFixed(1) + '°C';
                                    break;
                                case 'humidity':
                                    label += context.parsed.y.toFixed(0) + '%';
                                    break;
                                case 'battery':
                                    label += context.parsed.y.toFixed(2) + 'V';
                                    break;
                                default:
                                    label += context.parsed.y;
                            }
                        }
                        return label;
                    }
                }
            }
        },
        scales: {
            x: {
                type: 'time',
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)',
                    drawBorder: false
                }
            },
            temperature: {
                type: 'linear',
                display: true,
                position: 'left',
                title: {
                    display: true,
                    text: 'Temperature (°C)',
                    color: '#666',
                    font: {
                        size: 12,
                        weight: 'normal'
                    },
                    padding: 10
                },
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    padding: 10,
                    color: '#666',
                    callback: value => value.toFixed(1) + '°C'
                }
            },
            humidity: {
                type: 'linear',
                display: true,
                position: 'right',
                title: {
                    display: true,
                    text: 'Humidity (%)',
                    color: '#666',
                    font: {
                        size: 12,
                        weight: 'normal'
                    },
                    padding: 10
                },
                grid: {
                    display: false,
                    drawBorder: false
                },
                ticks: {
                    padding: 10,
                    color: '#666',
                    callback: value => value.toFixed(0) + '%'
                }
            },
            battery: {
                type: 'linear',
                display: true,
                position: 'right',
                title: {
                    display: true,
                    text: 'Battery (V)',
                    color: '#666',
                    font: {
                        size: 12,
                        weight: 'normal'
                    },
                    padding: 10
                },
                grid: {
                    display: false,
                    drawBorder: false
                },
                ticks: {
                    padding: 10,
                    color: '#666',
                    callback: value => value.toFixed(2) + 'V'
                }
            }
        },
        elements: {
            line: {
                tension: 0.4,
                borderWidth: 2
            },
            point: {
                radius: 0,
                hitRadius: 8,
                hoverRadius: 4
            }
        }
    },

    // Dataset styling
    DATASET_STYLES: {
        temperature: {
            borderColor: 'rgba(255, 99, 132, 0.8)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            yAxisID: 'temperature',
            hidden: false,
            fill: true
        },
        humidity: {
            borderColor: 'rgba(54, 162, 235, 0.8)',
            backgroundColor: 'rgba(54, 162, 235, 0.1)',
            yAxisID: 'humidity',
            hidden: false,
            fill: true
        },
        battery: {
            borderColor: 'rgba(75, 192, 192, 0.8)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            yAxisID: 'battery',
            hidden: false,
            fill: true
        }
    },

    // Date picker configuration
    DATE_PICKER_OPTIONS: {
        mode: "range",
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        defaultHour: 0,
        time_24hr: true,
        maxDate: "today",
        locale: {
            firstDayOfWeek: 1
        }
    }
};
