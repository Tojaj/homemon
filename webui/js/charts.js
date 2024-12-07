class ChartManager {
    constructor() {
        this.charts = new Map(); // Map of sensorId -> Chart instance
        this.originalData = new Map(); // Map of sensorId -> original measurements
        this.smoothingEnabled = false;
        this.windowSize = 5; // Size of moving average window
        this.initializeChartJs();
    }

    initializeChartJs() {
        // Set default font
        Chart.defaults.font.family = "'Inter', 'Helvetica', 'Arial', sans-serif";
    }

    // Calculate moving average for an array of data points
    calculateMovingAverage(data, windowSize) {
        if (!data || data.length === 0) return [];
        if (data.length < windowSize) return data;

        return data.map((point, index) => {
            const start = Math.max(0, index - Math.floor(windowSize / 2));
            const end = Math.min(data.length, start + windowSize);
            const window = data.slice(start, end);
            const sum = window.reduce((acc, curr) => acc + curr.y, 0);
            return {
                x: point.x,
                y: Number((sum / window.length).toFixed(2))
            };
        });
    }

    createChart(sensorId, container) {
        const canvas = container.querySelector('canvas');
        const ctx = canvas.getContext('2d');

        // Deep clone the default options
        const options = JSON.parse(JSON.stringify(CONFIG.CHART_OPTIONS));
        
        // Load saved dataset visibility states
        const datasetStates = JSON.parse(localStorage.getItem('datasetStates') || '{}');
        const sensorStates = datasetStates[sensorId] || {};
        
        // Create datasets with saved visibility states
        const datasets = [
            {
                label: 'Temperature',
                data: [],
                hidden: sensorStates.temperature === undefined ? false : !sensorStates.temperature,
                ...CONFIG.DATASET_STYLES.temperature
            },
            {
                label: 'Humidity',
                data: [],
                hidden: sensorStates.humidity === undefined ? false : !sensorStates.humidity,
                ...CONFIG.DATASET_STYLES.humidity
            },
            {
                label: 'Battery',
                data: [],
                hidden: sensorStates.battery === undefined ? false : !sensorStates.battery,
                ...CONFIG.DATASET_STYLES.battery
            }
        ];

        // Set initial axis visibility based on dataset visibility
        options.scales.temperature.display = !datasets[0].hidden;
        options.scales.humidity.display = !datasets[1].hidden;
        options.scales.battery.display = !datasets[2].hidden;

        const chart = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options
        });

        this.charts.set(sensorId, chart);
        return chart;
    }

    updateChartData(sensorId, measurements) {
        const chart = this.charts.get(sensorId);
        if (!chart) return;

        // Transform measurements into separate datasets
        const temperatureData = [];
        const humidityData = [];
        const batteryData = [];

        measurements.forEach(measurement => {
            const timestamp = DateTime.fromISO(measurement.timestamp).toJSDate();
            temperatureData.push({ x: timestamp, y: measurement.temperature });
            humidityData.push({ x: timestamp, y: measurement.humidity });
            batteryData.push({ x: timestamp, y: measurement.battery_voltage });
        });

        // Sort data by timestamp
        const sortByX = (a, b) => a.x - b.x;
        temperatureData.sort(sortByX);
        humidityData.sort(sortByX);
        batteryData.sort(sortByX);

        // Store original data
        this.originalData.set(sensorId, {
            temperature: [...temperatureData],
            humidity: [...humidityData],
            battery: [...batteryData]
        });

        // Apply smoothing if enabled
        const finalTempData = this.smoothingEnabled ? this.calculateMovingAverage(temperatureData, this.windowSize) : temperatureData;
        const finalHumidityData = this.smoothingEnabled ? this.calculateMovingAverage(humidityData, this.windowSize) : humidityData;
        const finalBatteryData = this.smoothingEnabled ? this.calculateMovingAverage(batteryData, this.windowSize) : batteryData;

        // Update datasets
        chart.data.datasets[0].data = finalTempData;
        chart.data.datasets[1].data = finalHumidityData;
        chart.data.datasets[2].data = finalBatteryData;

        // Adjust point radius based on number of measurements
        const isSinglePoint = measurements.length === 1;
        chart.options.elements.point = {
            radius: isSinglePoint ? 4 : 0,  // Show points only for single measurement
            hitRadius: 8,
            hoverRadius: 4,
            borderWidth: 2
        };

        // Determine if we need to show days based on the data range
        const firstDate = finalTempData[0]?.x;
        const lastDate = finalTempData[finalTempData.length - 1]?.x;
        if (firstDate && lastDate) {
            const daysDiff = Math.floor((lastDate - firstDate) / (1000 * 60 * 60 * 24));
            
            if (daysDiff > 0) {
                // Multi-day view
                chart.options.scales.x = {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        stepSize: 4, // Show time every 4 hours
                        displayFormats: {
                            hour: 'HH:mm',
                            day: 'MMM d'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkip: false,
                        callback: function(value, index, ticks) {
                            const date = new Date(value);
                            const hour = date.getHours();
                            const prevTick = index > 0 ? new Date(ticks[index - 1].value) : null;
                            
                            // Show date when it changes or at the start
                            if (!prevTick || prevTick.getDate() !== date.getDate()) {
                                return [
                                    DateTime.fromJSDate(date).toFormat('HH:mm'),
                                    DateTime.fromJSDate(date).toFormat('MMM d')
                                ];
                            }
                            // Show time for every 4 hours
                            if (hour % 4 === 0) {
                                return DateTime.fromJSDate(date).toFormat('HH:mm');
                            }
                            return '';
                        },
                        padding: 10,
                        color: '#666'
                    }
                };
            } else {
                // Single-day view
                chart.options.scales.x = {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: {
                            hour: 'HH:mm'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        padding: 10,
                        color: '#666'
                    }
                };
            }
        }

        chart.update('none'); // Update without animation for better performance
    }

    toggleDataset(type, visible) {
        this.charts.forEach((chart, sensorId) => {
            const dataset = chart.data.datasets.find(ds => ds.yAxisID === type);
            if (dataset) {
                dataset.hidden = !visible;
                // Also toggle the visibility of the corresponding Y axis
                chart.options.scales[type].display = visible;
            }
            chart.update('none');

            // Save dataset visibility state
            const datasetStates = JSON.parse(localStorage.getItem('datasetStates') || '{}');
            if (!datasetStates[sensorId]) {
                datasetStates[sensorId] = {};
            }
            datasetStates[sensorId][type] = visible;
            localStorage.setItem('datasetStates', JSON.stringify(datasetStates));
        });
    }

    toggleSmoothing(enabled) {
        this.smoothingEnabled = enabled;
        // Save smoothing state
        localStorage.setItem('smoothingEnabled', enabled);
        
        // Update all charts with smoothing setting
        this.charts.forEach((chart, sensorId) => {
            const originalData = this.originalData.get(sensorId);
            if (originalData) {
                if (enabled) {
                    // Apply smoothing to original data
                    chart.data.datasets[0].data = this.calculateMovingAverage([...originalData.temperature], this.windowSize);
                    chart.data.datasets[1].data = this.calculateMovingAverage([...originalData.humidity], this.windowSize);
                    chart.data.datasets[2].data = this.calculateMovingAverage([...originalData.battery], this.windowSize);
                } else {
                    // Restore original data
                    chart.data.datasets[0].data = [...originalData.temperature];
                    chart.data.datasets[1].data = [...originalData.humidity];
                    chart.data.datasets[2].data = [...originalData.battery];
                }
                chart.update('none');
            }
        });
    }

    destroyChart(sensorId) {
        const chart = this.charts.get(sensorId);
        if (chart) {
            chart.destroy();
            this.charts.delete(sensorId);
            this.originalData.delete(sensorId);
        }
    }

    destroyAllCharts() {
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
        this.originalData.clear();
    }

    resizeChart(sensorId) {
        const chart = this.charts.get(sensorId);
        if (chart) {
            chart.resize();
        }
    }

    resizeAllCharts() {
        this.charts.forEach(chart => chart.resize());
    }

    // Helper method to format date ranges for chart titles
    static formatDateRange(startDate, endDate) {
        const start = DateTime.fromISO(startDate);
        const end = DateTime.fromISO(endDate);
        return `${start.toFormat('dd LLL yyyy HH:mm')} - ${end.toFormat('dd LLL yyyy HH:mm')}`;
    }
}

// Create a global chart manager instance
const chartManager = new ChartManager();
