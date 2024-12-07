class DataLoader {
    static async loadLibraryData() {
        try {
            const response = await fetch('data/library_data.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const rawData = await response.json();
            
            if (!rawData.data || !Array.isArray(rawData.data.level1) || rawData.data.level1.length === 0) {
                throw new Error('Invalid or empty data structure');
            }
            
            // Store complete data in localStorage
            localStorage.setItem('completeLibraryData', JSON.stringify(rawData));
            return rawData;
        } catch (error) {
            console.error('Error loading library data:', error);
            return null;
        }
    }

    static getSecondaryTopicData(topicName) {
        try {
            const completeDataStr = localStorage.getItem('completeLibraryData');
            if (!completeDataStr) {
                throw new Error('Complete data not found in localStorage');
            }

            const completeData = JSON.parse(completeDataStr);
            if (!completeData || !completeData.data) {
                throw new Error('Invalid complete data structure');
            }

            const decodedTopicName = decodeURIComponent(topicName);
            const level1Data = completeData.data.level1.find(item => item.name === decodedTopicName);
            
            if (!level1Data) {
                throw new Error(`Topic "${decodedTopicName}" not found in level1 data`);
            }

            // Return the data in the expected format
            return {
                name: level1Data.name,
                children: level1Data.children.map(item => ({
                    name: item.name,
                    value: item.value || 1,
                    details: {
                        initial: item.initial || '',
                        children: item.children || []
                    }
                }))
            };
        } catch (error) {
            console.error('Error getting secondary topic data:', error);
            return null;
        }
    }
}

// Export for use in other files
window.DataLoader = DataLoader;
