class ApiService {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.axios = axios.create({
            baseURL: baseUrl,
            timeout: 10000,
            headers: {
                'Accept': 'application/json'
            }
        });

        // Add response interceptor for error handling
        this.axios.interceptors.response.use(
            response => response,
            error => {
                console.error('API Error:', error.response || error);
                throw new Error(
                    error.response?.data?.detail || 
                    error.message || 
                    'An error occurred while fetching data'
                );
            }
        );
    }

    async getSensors() {
        try {
            const response = await this.axios.get(CONFIG.ENDPOINTS.SENSORS);
            return response.data;
        } catch (error) {
            console.error('Error fetching sensors:', error);
            throw error;
        }
    }

    async getRecentMeasurements() {
        try {
            const response = await this.axios.get(CONFIG.ENDPOINTS.RECENT);
            return response.data;
        } catch (error) {
            console.error('Error fetching recent measurements:', error);
            throw error;
        }
    }

    async getMeasurements(sensorId, startTime, endTime) {
        try {
            const params = new URLSearchParams();
            if (startTime) {
                params.append('start_time', startTime);
            }
            if (endTime) {
                params.append('end_time', endTime);
            }

            const url = `${CONFIG.ENDPOINTS.MEASUREMENTS}/${sensorId}${params.toString() ? '?' + params.toString() : ''}`;
            const response = await this.axios.get(url);
            return response.data;
        } catch (error) {
            console.error(`Error fetching measurements for sensor ${sensorId}:`, error);
            throw error;
        }
    }

    async getSensorStats(sensorId, startTime, endTime) {
        try {
            const params = new URLSearchParams();
            if (startTime) {
                params.append('start_time', startTime);
            }
            if (endTime) {
                params.append('end_time', endTime);
            }

            const url = CONFIG.ENDPOINTS.STATS.replace('{sensor_id}', sensorId) + 
                       (params.toString() ? '?' + params.toString() : '');
            const response = await this.axios.get(url);
            return response.data;
        } catch (error) {
            console.error(`Error fetching stats for sensor ${sensorId}:`, error);
            throw error;
        }
    }

    async getSensorTrend(sensorId, startTime, endTime) {
        try {
            const params = new URLSearchParams();
            if (startTime) {
                params.append('start_time', startTime);
            }
            if (endTime) {
                params.append('end_time', endTime);
            }

            const url = CONFIG.ENDPOINTS.TREND.replace('{sensor_id}', sensorId) + 
                       (params.toString() ? '?' + params.toString() : '');
            const response = await this.axios.get(url);
            return response.data;
        } catch (error) {
            console.error(`Error fetching trend for sensor ${sensorId}:`, error);
            throw error;
        }
    }
}

// Create a global API service instance
const apiService = new ApiService(CONFIG.API_BASE_URL);
