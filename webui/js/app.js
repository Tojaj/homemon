class App {
    constructor() {
        this.sensors = [];
        this.dateRange = null;
        this.initializeDatePicker();
        this.initializeToggles();
        this.initializeEventListeners();
        this.loadData();
    }

    async initializeDatePicker() {
        // Initialize flatpickr without default dates
        this.dateRange = flatpickr("#dateRange", {
            ...CONFIG.DATE_PICKER_OPTIONS,
            onChange: (selectedDates) => {
                if (selectedDates.length === 2) {
                    this.updateAllCharts();
                }
            }
        });
    }

    loadSavedStates() {
        // Load toggle states
        const toggleStates = JSON.parse(localStorage.getItem('toggleStates') || '{}');
        
        // Set toggle states with defaults if not saved
        const tempToggle = document.getElementById('tempToggle');
        const humidityToggle = document.getElementById('humidityToggle');
        const batteryToggle = document.getElementById('batteryToggle');

        tempToggle.checked = toggleStates.temperature !== undefined ? toggleStates.temperature : true;
        humidityToggle.checked = toggleStates.humidity !== undefined ? toggleStates.humidity : true;
        batteryToggle.checked = toggleStates.battery !== undefined ? toggleStates.battery : true;

        // Apply toggle states to charts
        chartManager.toggleDataset('temperature', tempToggle.checked);
        chartManager.toggleDataset('humidity', humidityToggle.checked);
        chartManager.toggleDataset('battery', batteryToggle.checked);
    }

    saveToggleStates() {
        const toggleStates = {
            temperature: document.getElementById('tempToggle').checked,
            humidity: document.getElementById('humidityToggle').checked,
            battery: document.getElementById('batteryToggle').checked
        };
        localStorage.setItem('toggleStates', JSON.stringify(toggleStates));
    }

    saveGraphState(sensorId, isCollapsed) {
        const graphStates = JSON.parse(localStorage.getItem('graphStates') || '{}');
        graphStates[sensorId] = isCollapsed;
        localStorage.setItem('graphStates', JSON.stringify(graphStates));
    }

    initializeToggles() {
        const tempToggle = document.getElementById('tempToggle');
        const humidityToggle = document.getElementById('humidityToggle');
        const batteryToggle = document.getElementById('batteryToggle');

        tempToggle.addEventListener('change', (e) => {
            chartManager.toggleDataset('temperature', e.target.checked);
            this.saveToggleStates();
        });

        humidityToggle.addEventListener('change', (e) => {
            chartManager.toggleDataset('humidity', e.target.checked);
            this.saveToggleStates();
        });

        batteryToggle.addEventListener('change', (e) => {
            chartManager.toggleDataset('battery', e.target.checked);
            this.saveToggleStates();
        });
    }

    initializeEventListeners() {
        window.addEventListener('resize', () => {
            chartManager.resizeAllCharts();
        });

        document.addEventListener('click', (e) => {
            if (e.target.closest('.toggle-graph')) {
                const container = e.target.closest('.sensor-container');
                const wasCollapsed = container.classList.contains('collapsed');
                const icon = e.target.closest('.toggle-graph').querySelector('i');
                
                container.classList.toggle('collapsed');
                
                // Toggle between chevron-up and chevron-down
                icon.classList.remove(wasCollapsed ? 'bi-chevron-down' : 'bi-chevron-up');
                icon.classList.add(wasCollapsed ? 'bi-chevron-up' : 'bi-chevron-down');
                
                const sensorId = container.dataset.sensorId;
                this.saveGraphState(sensorId, !wasCollapsed);
                setTimeout(() => chartManager.resizeChart(sensorId), 300);
            }
        });
    }

    async loadData() {
        try {
            // Show loading state
            document.getElementById('sensorGraphs').innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';

            // Fetch sensors
            this.sensors = await apiService.getSensors();
            
            if (!this.sensors || this.sensors.length === 0) {
                throw new Error('No sensors found');
            }

            // Create graph containers
            this.createSensorContainers();
            
            // Get recent measurements to find the latest data
            const recentMeasurements = await apiService.getRecentMeasurements();
            
            if (recentMeasurements && recentMeasurements.length > 0) {
                // Find the latest measurement date
                const latestDate = recentMeasurements.reduce((latest, measurement) => {
                    const measurementDate = DateTime.fromISO(measurement.timestamp);
                    return latest ? (measurementDate > latest ? measurementDate : latest) : measurementDate;
                }, null);

                if (latestDate) {
                    // Set date range to the day of the latest measurement
                    const startOfDay = latestDate.startOf('day');
                    const endOfDay = latestDate.endOf('day');
                    
                    // Update the date picker with the date range
                    this.dateRange.setDate([startOfDay.toJSDate(), endOfDay.toJSDate()]);
                    
                    // Explicitly trigger the chart update with the proper time range
                    const measurementPromises = this.sensors.map(async sensor => {
                        try {
                            const measurements = await apiService.getMeasurements(
                                sensor.id,
                                startOfDay.toISO(),
                                endOfDay.toISO()
                            );
                            if (measurements && measurements.length > 0) {
                                chartManager.updateChartData(sensor.id, measurements);
                            }
                        } catch (error) {
                            console.error(`Error fetching data for sensor ${sensor.id}:`, error);
                        }
                    });

                    await Promise.all(measurementPromises);

                    // Load saved states after charts are created and data is loaded
                    this.loadSavedStates();
                }
            } else {
                throw new Error('No measurements found');
            }
        } catch (error) {
            console.error('Error loading data:', error);
            document.getElementById('sensorGraphs').innerHTML = `
                <div class="alert alert-danger" role="alert">
                    ${error.message || 'Error loading sensor data. Please try refreshing the page.'}
                </div>
            `;
        }
    }

    createSensorContainers() {
        const container = document.getElementById('sensorGraphs');
        container.innerHTML = '';
        
        const template = document.getElementById('sensorTemplate');
        const graphStates = JSON.parse(localStorage.getItem('graphStates') || '{}');
        
        this.sensors.forEach(sensor => {
            const clone = template.content.cloneNode(true);
            const sensorContainer = clone.querySelector('.sensor-container');
            
            sensorContainer.dataset.sensorId = sensor.id;
            const titleElement = clone.querySelector('.sensor-title');
            
            // Create separate spans for sensor name and MAC address
            const nameSpan = document.createElement('span');
            nameSpan.textContent = sensor.alias || `Sensor ${sensor.id}`;
            
            const macSpan = document.createElement('span');
            macSpan.className = 'sensor-mac';
            macSpan.textContent = sensor.mac_address;
            
            titleElement.innerHTML = ''; // Clear existing content
            titleElement.appendChild(nameSpan);
            titleElement.appendChild(macSpan);
            
            // Apply saved collapse state and set initial chevron direction
            const icon = clone.querySelector('.toggle-graph i');
            if (graphStates[sensor.id]) {
                sensorContainer.classList.add('collapsed');
                icon.classList.remove('bi-chevron-up');
                icon.classList.add('bi-chevron-down');
            } else {
                icon.classList.remove('bi-chevron-down');
                icon.classList.add('bi-chevron-up');
            }
            
            container.appendChild(clone);
            
            // Create chart for this sensor
            chartManager.createChart(sensor.id, sensorContainer);
        });
    }

    async updateAllCharts() {
        const [startDate, endDate] = this.dateRange.selectedDates;
        
        if (!startDate || !endDate) return;

        // Set time to start of day for start date and end of day for end date
        const startDateTime = DateTime.fromJSDate(startDate).startOf('day');
        const endDateTime = DateTime.fromJSDate(endDate).endOf('day');

        try {
            const measurementPromises = this.sensors.map(async sensor => {
                try {
                    const measurements = await apiService.getMeasurements(
                        sensor.id,
                        startDateTime.toISO(),
                        endDateTime.toISO()
                    );
                    if (measurements && measurements.length > 0) {
                        chartManager.updateChartData(sensor.id, measurements);
                    }
                } catch (error) {
                    console.error(`Error fetching data for sensor ${sensor.id}:`, error);
                    // Continue with other sensors even if one fails
                }
            });

            await Promise.all(measurementPromises);
        } catch (error) {
            console.error('Error updating charts:', error);
            const errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-danger alert-dismissible fade show';
            errorAlert.innerHTML = `
                Error updating charts: ${error.message || 'Please try again.'}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('header').appendChild(errorAlert);
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
