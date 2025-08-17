import React, { useMemo } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Text, Card } from 'react-native-paper';

const { width: screenWidth } = Dimensions.get('window');

const SpeedChart = ({ data, title = 'Speed Over Time', period = '1h' }) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        labels: ['No Data'],
        datasets: [{
          data: [0],
          strokeWidth: 2,
        }],
      };
    }

    // Process data based on period
    let processedData = [];
    
    if (period === '1h') {
      // Show last 12 data points (5-minute intervals)
      processedData = data.slice(-12);
    } else if (period === '24h') {
      // Group by hour, show last 24 hours
      processedData = groupDataByHour(data);
    } else {
      // Default: show last 10 data points
      processedData = data.slice(-10);
    }

    const labels = processedData.map((item, index) => {
      if (period === '24h') {
        return `${item.hour}:00`;
      } else {
        const time = new Date(item.timestamp);
        return `${time.getHours()}:${time.getMinutes().toString().padStart(2, '0')}`;
      }
    });

    const speeds = processedData.map(item => item.speed || item.avgSpeed || 0);

    return {
      labels,
      datasets: [{
        data: speeds,
        strokeWidth: 3,
        color: (opacity = 1) => `rgba(33, 150, 243, ${opacity})`,
      }],
    };
  }, [data, period]);

  const groupDataByHour = (data) => {
    const grouped = {};
    
    data.forEach(item => {
      const hour = new Date(item.timestamp).getHours();
      if (!grouped[hour]) {
        grouped[hour] = [];
      }
      grouped[hour].push(item);
    });

    return Object.keys(grouped).map(hour => ({
      hour: parseInt(hour),
      avgSpeed: grouped[hour].reduce((sum, item) => sum + item.speed, 0) / grouped[hour].length,
      maxSpeed: Math.max(...grouped[hour].map(item => item.speed)),
      count: grouped[hour].length,
    }));
  };

  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 1,
    color: (opacity = 1) => `rgba(33, 150, 243, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: '#2196F3',
      fill: '#ffffff',
    },
    propsForBackgroundLines: {
      strokeWidth: 1,
      stroke: '#e0e0e0',
    },
  };

  const maxSpeed = useMemo(() => {
    if (!data || data.length === 0) return 0;
    return Math.max(...data.map(item => item.speed || 0));
  }, [data]);

  const avgSpeed = useMemo(() => {
    if (!data || data.length === 0) return 0;
    const sum = data.reduce((acc, item) => acc + (item.speed || 0), 0);
    return sum / data.length;
  }, [data]);

  return (
    <Card style={styles.container}>
      <Card.Content>
        <Text variant="titleMedium" style={styles.title}>
          {title}
        </Text>
        
        <View style={styles.statsContainer}>
          <View style={styles.statItem}>
            <Text variant="bodySmall" style={styles.statLabel}>Max Speed</Text>
            <Text variant="titleLarge" style={styles.statValue}>
              {maxSpeed.toFixed(1)} km/h
            </Text>
          </View>
          <View style={styles.statItem}>
            <Text variant="bodySmall" style={styles.statLabel}>Avg Speed</Text>
            <Text variant="titleLarge" style={styles.statValue}>
              {avgSpeed.toFixed(1)} km/h
            </Text>
          </View>
        </View>

        <View style={styles.chartContainer}>
          <LineChart
            data={chartData}
            width={screenWidth - 60}
            height={220}
            chartConfig={chartConfig}
            bezier
            style={styles.chart}
            yAxisLabel=""
            yAxisSuffix=" km/h"
            withInnerLines={true}
            withOuterLines={true}
            withVerticalLines={true}
            withHorizontalLines={true}
          />
        </View>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: 16,
    elevation: 4,
  },
  title: {
    textAlign: 'center',
    marginBottom: 16,
    color: '#333',
    fontWeight: 'bold',
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    color: '#666',
    marginBottom: 4,
  },
  statValue: {
    color: '#2196F3',
    fontWeight: 'bold',
  },
  chartContainer: {
    alignItems: 'center',
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
});

export default SpeedChart;