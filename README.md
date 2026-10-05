# inno-Abadan-Petrochemical-Smart-Dash
# Design of the CBM Smart Dashboard for Abadan Petrochemical


## 1. Complete study of Abadan Petrochemical

### 1-1. History and location

Abadan Petrochemical was built in 1967 (1346 SH) by the American company Lummus and came into operation in 1969 (1348 SH). The complex is located on a 50-hectare site in Motahari district, Abadan. During 1980 to 1988 (1359–1367 SH) it was destroyed by the imposed war and was subsequently rebuilt by domestic specialists.

### 1-2. Products and production capacity

The initial annual production capacity included the following:
- **20,000 tons** of PVC
- **10,000 tons** of dodecylbenzene (DDB)
- **24,000 tons** of caustic soda

In 1975 (1354 SH) an expansion plan to increase PVC production to **60,000 tons** per year was carried out. PVC production rose to about 60,000 tons in 2005 (1384 SH), and the future development goal is to reach an annual production of **110,000 tons** of PVC. Abadan Petrochemical also produces **30,000 tons of caustic soda** and **10,000 tons of dodecylbenzene**.

### 1-3. Production units

The key production units include units 200.300, 400.500, 600.700, 800.900 and 1000, and new PVC, tetramer and DDB production units have also recently been commissioned. The vital feedstocks of the complex include EDC, VCM, chlorine and gas.

### 1-4. Environmental conditions

The complex is located in an area with harsh climatic conditions:
- Maximum design temperature: **49 degrees Celsius**
- Absolute maximum temperature: **55 degrees Celsius**
- Minimum temperature: **-5 degrees Celsius**
- Relative humidity: maximum 100% and minimum 4%
- Altitude above sea level: 1.5 meters

### 1-5. Equipment status

Given the complex's age (more than 55 years) and the effects of the war, **aging equipment** is one of the main challenges. The company has put a renewal program for aging equipment in key units on its agenda.


## 2. Overall architecture of the CBM smart dashboard system

### 2-1. Architecture layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation layer (Dashboard)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Heat map   │ │ Equipment│ │ Failure  │ │ Real-time│         │
│  │ of equip.  │ │ health   │ │ forecast │ │ alerts   │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
├─────────────────────────────────────────────────────────────────┤
│                    Analysis layer (AI/ML Engine)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Pattern  │ │ RUL      │ │ Spectral │ │ Auto     │         │
│  │ detection│ │ forecast │ │ analysis │ │ Operation│         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
├─────────────────────────────────────────────────────────────────┤
│                    Processing layer (Edge/Cloud)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ FFT /    │ │ Noise   │ │ Feature  │ │ Data     │         │
│  │ Wavelet  │ │ filter  │ │ Extraction│ │ Fusion   │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
├─────────────────────────────────────────────────────────────────┤
│                    Data layer (Data Acquisition)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Vibration│ │ Acoustic │ │ Thermal  │ │ Process  │         │
│  │ sensors  │ │ sensors  │ │ cameras  │ │ data     │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2-2. Reference standards

The system is designed based on the following standards:
- **ISO 17359**: General guidelines for condition monitoring and diagnostics of machines
- **ISO 14224**: Collection of reliability and maintenance data for equipment
- **ISO 13374**: Condition monitoring data processing


## 3. System inputs (Inputs)

### 3-1. Vibration sensors (Vibration Sensors)

| Sensor type | Quantity | Installation location | Measurement range |
|-----------|-------|----------|-------------------|
| Triaxial accelerometer (IEPE) | 200+ | On bearings of compressors, pumps, fans | 0-50 kHz |
| Velocity sensor (Velometer) | 100+ | On the casing of rotating equipment | 0-100 mm/s |
| Displacement sensor (Proximity Probe) | 50+ | On the shaft of turbines and large compressors | 0-2 mm |

### 3-2. Acoustic sensors (Acoustic Sensors)

| Sensor type | Quantity | Installation location | Application |
|-----------|-------|----------|--------|
| High-frequency microphone (Ultrasonic) | 80+ | Near bearings and valves | Leak and friction detection |
| Broadband acoustic sensor | 50+ | Environment of production units | Ambient noise analysis |
| AE sensor (Acoustic Emission) | 30+ | On pressure vessels and pipelines | Crack detection |

### 3-3. Smart and thermal cameras

| Camera type | Quantity | Installation location | Application |
|------------|-------|----------|--------|
| Thermal camera (Thermal Imaging) | 25+ | Strategic points of the units | Monitoring equipment temperature and thermal leaks |
| Smart CCTV camera (AI-Enabled CCTV) | 40+ | Throughout the complex | Detection of leaks, flame, smoke and abnormal behavior |
| Hyperspectral camera (Hyperspectral) | 5+ | Key units | Gas leak detection |

### 3-4. Process sensors

| Sensor type | Quantity | Measured parameters |
|-----------|-------|----------------------|
| Pressure sensor | 150+ | Line, tank and reactor pressure |
| Temperature sensor (RTD/TC) | 200+ | Process temperature at various points |
| Flow meter (Flow Meter) | 100+ | Feed and product flow |
| Level sensor (Level) | 80+ | Level of tanks and towers |
| Gas detector (Gas Detector) | 120+ | Detection of flammable and toxic gases |

### 3-5. Other input data

- **DCS/PLC data**: operating parameters from the distributed control system
- **Maintenance data**: repair records, part replacements, inspections
- **Environmental data**: temperature, humidity, atmospheric pressure
- **Operational data**: equipment load, motor speed, electric current


## 4. System outputs (Outputs)

### 4-1. Main dashboard

| Dashboard section | Output content | Display format |
|-------------|--------------|------------|
| **Complex overview** | 3D heat map of the status of all equipment | Graphical display with color codes |
| **Equipment health** | Health index of each equipment (0-100) | Gauge/colored progress bar |
| **Failure prediction** | RUL (Remaining Useful Life) of each equipment | Number + trend chart |
| **Alerts** | Real-time alerts with prioritization | List with color code |
| **Vibration analysis** | Frequency spectrum, waveform, trends | FFT and Waterfall charts |
| **Acoustic analysis** | Acoustic patterns, leak detection | Chart and audio display |
| **Auto Operation performance** | Status of automatic actions performed | Performance report |

### 4-2. Analytical outputs

- **Daily/weekly/monthly reports**: summary of equipment status and recommended actions
- **Predictive alerts**: notifications of imminent failure with an exact estimated time
- **Maintenance instructions**: detailed recommendations for each identified fault type
- **Cost-benefit report**: return-on-investment analysis of the CBM system
- **AI performance report**: detection accuracy, false alarm rate, model improvements


## 5. Sensors and their health monitoring

### 5-1. Sensor health color codes

Based on industry standards:

| Color | Status | Meaning | Required action |
|-----|-------|------|----------------|
| **Green** | Healthy (Normal) | The sensor works correctly and sends valid data | Normal monitoring |
| **Yellow** | Warning (Warning) | The sensor deviates from the optimal state or needs calibration | Check and recalibrate |
| **Orange** | Fault (Fault) | The sensor is faulty or sends invalid data | Replace or repair the sensor |

### 5-2. Sensor health monitoring parameters

Each sensor is automatically monitored for the following:
1. **Supply voltage**: allowed range 24V ± 5%
2. **Output signal**: check the 4-20mA range
3. **Signal quality**: signal-to-noise ratio (SNR)
4. **Measurement accuracy**: deviation from the reference value
5. **Communication**: data transmission rate and delay
6. **Operating temperature**: sensor temperature within the allowed range


## 6. Smart Operator (Auto Operation)

### 6-1. Definition of Auto Operation

The Auto Operation system is designed inspired by leading industry solutions such as **Honeywell Experion Cognition** and **ABB Ability Genix**, the first examples of which in the petrochemical industry were implemented by **Borouge** in the UAE.

### 6-2. Smart operator tasks

| Level | Task | Description |
|-----|-------|------|
| **Level 1: Monitoring** | Automatic monitoring | 24/7 monitoring of all sensors and equipment |
| **Level 2: Analysis** | Intelligent analysis | Detection of failure patterns with accuracy > 95% |
| **Level 3: Alerting** | Intelligent alerting | Sending alerts with prioritization and documentation |
| **Level 4: Recommendation** | Providing solutions | Proposing precise corrective actions |
| **Level 5: Action** | Automatic execution | Performing actions without the need for a human operator |

### 6-3. Executable automatic actions

1. **Automatic parameter adjustment**: changing motor speed, flow, pressure according to conditions
2. **Automatic line switching**: switching to the backup production line in case of failure
3. **Automatic parts request**: sending a spare parts request to the warehouse
4. **Automatic maintenance scheduling**: setting the maintenance time based on priority
5. **Automatic reporting**: sending reports to managers and the relevant teams


## 7. Benchmark with global examples

### 7-1. Comparison with similar global systems

| Feature | Proposed system | ABB Ability | Honeywell Forge | AVEVA Digital Twin |
|-------|---------------|-------------|-----------------|-------------------|
| **Vibration analysis** | ✅ Advanced (AI) | ✅ | ✅ | ✅ |
| **Acoustic analysis** | ✅ | ❌ | ❌ | ❌ |
| **Thermal camera** | ✅ | ✅ | ✅ | ❌ |
| **AI/ML fault detection** | ✅ LSTM+CNN | ✅ Genix | ✅ | ✅ |
| **Auto Operation** | ✅ | ⚠️ Limited | ✅ Experion | ❌ |
| **Sensor health monitoring** | ✅ | ✅ | ✅ | ❌ |
| **Smart dashboard** | ✅ | ✅ | ✅ | ✅ |
| **Reliability** | > 99% | 99% | 99% | 98% |

### 7-2. Strengths relative to global examples

1. **Integration of acoustic and vibration analysis**: global examples usually use only vibration
2. **Full equipment camera coverage**: visual and thermal monitoring of all equipment
3. **Complete Auto Operation system**: similar to the leading Borouge project in the UAE
4. **Sensor health monitoring with color codes**: increases data reliability
5. **More suitable implementation cost**: use of domestic capacity

### 7-3. Areas for improvement relative to global examples

1. **Supply chain integration**: connection to spare part suppliers' systems
2. **Complete 3D digital twin**: similar to AVEVA
3. **Preventive maintenance recommender system**: based on cost-benefit analysis


## 8. Items added to the system

### 8-1. Full production line coverage with cameras

All production units including:
- Units 200.300, 400.500, 600.700, 800.900 and 1000
- New PVC, tetramer and DDB production units
- Chlor-alkali unit
- Storage tanks and pipelines

### 8-2. Sensor health monitoring with color codes

A system similar to industry standards for displaying sensor status:
- **Green**: normal operation
- **Yellow**: needs check/calibration
- **Orange**: failure/needs replacement

### 8-3. Complete Auto Operation system

With capabilities beyond global examples, including:
- Automatic detection of failure patterns with accuracy > 95%
- Automatic proposal and execution of corrective actions
- 20% reduction in unplanned downtime (similar to Borouge results)


## 9. SRS documents (Software Requirements Specification)

### SRS document of the Abadan Petrochemical CBM smart dashboard system

---

#### 1. Introduction

##### 1-1. Purpose
This document specifies the software requirements of the smart condition-based monitoring (CBM) dashboard system for Abadan Petrochemical. The main goal is to increase the efficiency of aging equipment through vibration and acoustic analysis using artificial intelligence.

##### 1-2. Scope
The system includes monitoring of 500+ rotating equipment, 800+ sensors, 40+ smart and thermal cameras, and an Auto Operation system for all production units of the complex.

##### 1-3. Audience
- Senior and middle managers of the petrochemical
- Control room operators
- Maintenance and repair team
- Operations engineers
- HSE team

---

#### 2. General system requirements

##### 2-1. Hardware requirements

| Component | Specifications | Quantity |
|-------|--------|-------|
| Central server | 2x Intel Xeon, 256GB RAM, 10TB Storage | 2 (Active-Active) |
| Edge servers | 4x Intel Xeon, 64GB RAM, 2TB Storage | 5 units |
| Workstations | Core i7, 32GB RAM, 4K Monitor | 10 units |
| Network | Fiber Optic 10GbE + Wireless Mesh | - |
| Storage | SAN with redundancy + Cloud Backup | 50TB |

##### 2-2. Software requirements

| Component | Specifications |
|-------|--------|
| Operating system | Linux (Ubuntu 22.04 LTS) / Windows Server 2022 |
| Database | Time-Series (InfluxDB) + SQL (PostgreSQL) |
| AI platform | TensorFlow 2.x / PyTorch |
| Dashboard | React.js / Grafana |
| Messaging | MQTT / Kafka |
| Security | TLS 1.3, RBAC, 2FA |

---

#### 3. Functional requirements (Functional Requirements)

##### 3-1. Data collection module

| Code | Requirement | Priority |
|----|----------|--------|
| FR-01 | The system must collect vibration data from all sensors at a sampling rate of at least 25.6 kHz | High |
| FR-02 | The system must collect acoustic data at a sampling rate of at least 44.1 kHz | High |
| FR-03 | The system must receive thermal images from cameras with a resolution of at least 640×480 pixels | Medium |
| FR-04 | The system must receive process data from the DCS at a rate of at least 1 Hz | High |
| FR-05 | The system must be able to synchronize data with ±1ms accuracy | High |

##### 3-2. Processing and analysis module

| Code | Requirement | Priority |
|----|----------|--------|
| FR-06 | The system must perform an FFT on vibration signals with a Hann window | High |
| FR-07 | The system must extract statistical features (RMS, Peak, Crest Factor, Kurtosis) | High |
| FR-08 | The system must implement LSTM and CNN models to detect failure patterns | High |
| FR-09 | The system must be able to detect 16 common fault types in rotating equipment | High |
| FR-10 | The system must perform acoustic spectral analysis for leak detection | Medium |

##### 3-3. Prediction module

| Code | Requirement | Priority |
|----|----------|--------|
| FR-11 | The system must estimate the RUL (Remaining Useful Life) of each equipment with ±5% accuracy | High |
| FR-12 | The system must issue predictive alerts at least 72 hours before failure | High |
| FR-13 | The system must display parameter trends for 7, 30 and 90-day periods | High |

##### 3-4. Auto Operation module

| Code | Requirement | Priority |
|----|----------|--------|
| FR-14 | The system must automatically change operating parameter settings based on equipment conditions | High |
| FR-15 | The system must automatically send maintenance requests to the relevant team | High |
| FR-16 | The system must automatically optimize the maintenance schedule | Medium |
| FR-17 | The system must have human confirmation capability for critical actions (Human-in-the-loop) | High |

##### 3-5. Dashboard and reporting module

| Code | Requirement | Priority |
|----|----------|--------|
| FR-18 | The system must provide a dashboard showing the real-time status of all equipment with color codes | High |
| FR-19 | The system must automatically generate daily, weekly and monthly reports | High |
| FR-20 | The system must be able to view data history and trends for different periods | High |
| FR-21 | The system must send alerts via email, SMS and in-app notification | High |

---

#### 4. Non-functional requirements (Non-Functional Requirements)

##### 4-1. Performance (Performance)

| Code | Requirement | Value |
|----|----------|-------|
| NFR-01 | Dashboard response time | < 2 seconds |
| NFR-02 | End-to-end data delay | < 500ms |
| NFR-03 | Vibration sampling rate | ≥ 25.6 kHz |
| NFR-04 | Concurrent processing capacity | ≥ 10,000 data points/second |
| NFR-05 | Recovery time after failure (RTO) | < 1 hour |

##### 4-2. Reliability (Reliability)

| Code | Requirement | Value |
|----|----------|-------|
| NFR-06 | System availability | ≥ 99.9% |
| NFR-07 | System MTBF | ≥ 8,760 hours |
| NFR-08 | Correct fault detection rate (Accuracy) | ≥ 95% |
| NFR-09 | False alarm rate (False Alarm Rate) | < 5% |

##### 4-3. Security (Security)

| Code | Requirement |
|----|----------|
| NFR-10 | All communications must be encrypted with TLS 1.3 |
| NFR-11 | The system must support two-factor authentication (2FA) |
| NFR-12 | Access must be managed based on roles (RBAC) |
| NFR-13 | All user activities must be logged |
| NFR-14 | The system must comply with the ISA/IEC 62443 standard |

##### 4-4. Scalability (Scalability)

| Code | Requirement |
|----|----------|
| NFR-15 | The system must be able to add new sensors up to 2000 |
| NFR-16 | The system must be able to add new equipment up to 1000 |
| NFR-17 | The system must use a microservices architecture for extensibility |

##### 4-5. Maintainability (Maintainability)

| Code | Requirement |
|----|----------|
| NFR-18 | The system must have complete technical and user documentation |
| NFR-19 | The source code must be written to clean code standards |
| NFR-20 | The system must be able to be updated without downtime (Zero-downtime) |

---

#### 5. User interfaces (User Interfaces)

##### 5-1. Main dashboard

Main dashboard pages:
1. **Overview page**: complex heat map with the status of all equipment
2. **Equipment page**: full details of each equipment with vibration and acoustic charts
3. **Alerts page**: list of active alerts with prioritization
4. **Prediction page**: equipment RUL and the proposed maintenance schedule
5. **Auto Operation page**: status of automatic actions and operation log
6. **Reports page**: analytical and statistical reports

##### 5-2. Color code display

| Color | Meaning at equipment level | Meaning at sensor level |
|-----|-------------------|-------------------|
| **Green** | Normal operation | Healthy sensor |
| **Yellow** | Deviation from optimal conditions | Needs calibration |
| **Orange** | Needs immediate action | Faulty sensor |

---

#### 6. Design constraints

| Code | Constraint |
|----|----------|
| DC-01 | The system must operate in an operating environment with a temperature of -5 to 55 degrees Celsius |
| DC-02 | The system must operate in an environment with 4-100% humidity |
| DC-03 | All equipment must have ATEX/IECEx certification for hazardous environments |
| DC-04 | The system must be compatible with the complex's existing DCS |
| DC-05 | The total power consumption of the system must not exceed 50 kW |


## 10. Synthetic data (Synthetic Data)

To ensure the correct operation of the dashboard and to train AI models, the following synthetic data is generated:

### 10-1. Synthetic vibration data

```python
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_vibration_data(equipment_id, duration_days=30, sample_rate=25600):
    """
    Generate synthetic vibration data for a specific equipment
    """
    t = np.linspace(0, duration_days*24*3600, duration_days*24*3600*sample_rate)
    
    # base frequencies (equipment specifications)
    rpm = np.random.randint(1000, 6000)  # revolutions per minute
    f0 = rpm / 60  # base frequency
    
    # healthy base signal
    signal = 0.5 * np.sin(2 * np.pi * f0 * t)
    signal += 0.3 * np.sin(2 * np.pi * 2*f0 * t)  # second harmonic
    signal += 0.15 * np.sin(2 * np.pi * 3*f0 * t)  # third harmonic
    
    # background noise
    noise = 0.05 * np.random.randn(len(t))
    signal += noise
    
    # simulating gradual failures
    fault_start = np.random.randint(5, duration_days-5)
    fault_type = np.random.choice(['unbalance', 'misalignment', 'bearing_fault', 'looseness'])
    
    if fault_type == 'unbalance':
        # unbalance: increased amplitude at the base frequency
        for i in range(int(fault_start * 24*3600 * sample_rate), len(t)):
            progress = (i - int(fault_start * 24*3600 * sample_rate)) / (len(t) - int(fault_start * 24*3600 * sample_rate))
            signal[i] += 0.3 * progress * np.sin(2 * np.pi * f0 * t[i])
    
    elif fault_type == 'misalignment':
        # misalignment: increased second harmonic
        for i in range(int(fault_start * 24*3600 * sample_rate), len(t)):
            progress = (i - int(fault_start * 24*3600 * sample_rate)) / (len(t) - int(fault_start * 24*3600 * sample_rate))
            signal[i] += 0.2 * progress * np.sin(2 * np.pi * 2*f0 * t[i])
    
    elif fault_type == 'bearing_fault':
        # bearing fault: high frequencies
        bpfo = 0.4 * f0 * 8  # Ball Pass Frequency Outer
        for i in range(int(fault_start * 24*3600 * sample_rate), len(t)):
            progress = (i - int(fault_start * 24*3600 * sample_rate)) / (len(t) - int(fault_start * 24*3600 * sample_rate))
            signal[i] += 0.15 * progress * np.sin(2 * np.pi * bpfo * t[i])
    
    # sampling for storage (reduce rate to reduce volume)
    downsample_factor = 100
    t_downsampled = t[::downsample_factor]
    signal_downsampled = signal[::downsample_factor]
    
    df = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(seconds=x) for x in t_downsampled],
        'equipment_id': equipment_id,
        'vibration_x': signal_downsampled + 0.02*np.random.randn(len(t_downsampled)),
        'vibration_y': signal_downsampled * 0.8 + 0.02*np.random.randn(len(t_downsampled)),
        'vibration_z': signal_downsampled * 0.6 + 0.02*np.random.randn(len(t_downsampled)),
        'rpm': rpm,
        'fault_type': fault_type if i > fault_start*24*3600*sample_rate else 'normal',
        'fault_progress': np.clip(progress, 0, 1) if i > fault_start*24*3600*sample_rate else 0
    })
    
    return df
```

### 10-2. Synthetic sensor health data

```python
def generate_sensor_health_data(num_sensors=800, duration_days=30):
    """
    Generate sensor health data with color codes
    """
    data = []
    for sensor_id in range(num_sensors):
        # initial state: most sensors are green
        initial_status = np.random.choice(['green', 'yellow', 'orange'], 
                                          p=[0.92, 0.06, 0.02])
        
        for day in range(duration_days):
            # gradual state change
            if initial_status == 'green':
                if np.random.random() < 0.01:  # 1% chance of failure per day
                    status = np.random.choice(['yellow', 'orange'], p=[0.6, 0.4])
                else:
                    status = 'green'
            elif initial_status == 'yellow':
                if np.random.random() < 0.05:  # 5% chance of recovery
                    status = 'green'
                elif np.random.random() < 0.1:  # 10% chance of worsening
                    status = 'orange'
                else:
                    status = 'yellow'
            else:  # orange
                if np.random.random() < 0.02:  # 2% chance of replacement
                    status = 'green'
                else:
                    status = 'orange'
            
            data.append({
                'sensor_id': sensor_id,
                'date': datetime.now().date() + timedelta(days=day),
                'status': status,
                'voltage': 24 + np.random.normal(0, 0.5),
                'temperature': 45 + np.random.normal(0, 5),
                'signal_quality': np.random.uniform(0.85, 1.0),
                'last_calibration': datetime.now() - timedelta(days=np.random.randint(0, 90))
            })
    
    return pd.DataFrame(data)
```

### 10-3. Synthetic RUL prediction data

```python
def generate_rul_data(equipment_id, fault_type, current_health):
    """
    Generate RUL (Remaining Useful Life) data for an equipment
    """
    # total useful life of the equipment (hours)
    total_life = np.random.randint(20000, 80000)
    
    # current age of the equipment (hours)
    current_age = np.random.randint(1000, total_life - 1000)
    
    # actual RUL
    true_rul = total_life - current_age
    
    # prediction error (error grows with age)
    prediction_error = np.random.normal(0, 0.05 * current_age / total_life)
    predicted_rul = true_rul * (1 + prediction_error)
    
    return {
        'equipment_id': equipment_id,
        'fault_type': fault_type,
        'total_life_hours': total_life,
        'current_age_hours': current_age,
        'true_rul_hours': true_rul,
        'predicted_rul_hours': max(0, predicted_rul),
        'confidence': 1 - abs(prediction_error),
        'health_score': current_health
    }
```

### 10-4. Auto Operation operational data

```python
def generate_auto_operation_logs(num_actions=1000):
    """
    Generate the Auto Operation automatic action log
    """
    actions = []
    for i in range(num_actions):
        action_type = np.random.choice([
            'parameter_adjustment',
            'maintenance_request',
            'line_switch',
            'alert_escalation',
            'report_generation'
        ], p=[0.4, 0.25, 0.15, 0.15, 0.05])
        
        status = np.random.choice(['success', 'failed', 'pending'], p=[0.85, 0.05, 0.1])
        
        actions.append({
            'action_id': i,
            'timestamp': datetime.now() - timedelta(hours=np.random.randint(0, 720)),
            'action_type': action_type,
            'equipment_id': np.random.randint(1, 500),
            'status': status,
            'execution_time_ms': np.random.randint(100, 5000),
            'human_override': np.random.choice([True, False], p=[0.1, 0.9]),
            'details': f"Auto {action_type} on equipment {np.random.randint(1, 500)}"
        })
    
    return pd.DataFrame(actions)
```

### 10-5. Required number of synthetic data points

| Data type | Record count | Approximate size |
|----------|-------------|------------|
| Vibration data (30 days × 800 sensors) | ~60 million | ~50 GB |
| Acoustic data (30 days × 130 sensors) | ~10 million | ~10 GB |
| Sensor health data (800 sensors × 30 days) | 24,000 | ~5 MB |
| RUL data (500 equipment × 30 days) | 15,000 | ~3 MB |
| Auto Operation data | 1,000 | ~1 MB |
| Process data (1000 points × 30 days) | ~2.6 million | ~200 MB |
| **Total** | **~73 million** | **~60 GB** |

### 10-6. Dashboard validation criteria

To ensure the accuracy and reliability of the dashboard, the following criteria are defined:

| Criterion | Target value | Verification method |
|-------|-----------|-----------|
| Fault detection accuracy | ≥ 95% | Comparison with real data and field test |
| False alarm rate | < 5% | Monitoring and logging of unwarranted alerts |
| RUL prediction accuracy | ±5% | Comparison with actual life after replacement |
| Response time | < 2 seconds | Load and stress test |
| Availability | ≥ 99.9% | System uptime monitoring |
| Sensor location accuracy | ±1 meter | GPS/localization test |
| Thermal image accuracy | ±2 degrees Celsius | Calibration with a reference thermometer |
| Acoustic analysis accuracy | ≥ 90% | Comparison with manual analysis |

---

## 11. Summary and conclusion

The proposed smart CBM dashboard system for Abadan Petrochemical is designed with the following features:

1. **Full equipment coverage**: more than 500 rotating equipment and 800 sensors
2. **Combined vibration and acoustic analysis**: a unique approach compared to competitors
3. **Sensor health monitoring**: with green, yellow and orange color codes
4. **Auto Operation**: an intelligent system with automatic action capability
5. **Full visual coverage**: 40+ smart and thermal cameras
6. **High accuracy**: fault detection with accuracy ≥ 95% and false alarm rate < 5%
7. **Compliance with global standards**: ISO 17359, ISO 14224, ISA/IEC 62443

This system is designed inspired by the best global examples such as **ABB Ability**, **Honeywell Forge** and **AVEVA Digital Twin**, and by adding unique capabilities such as **acoustic analysis**, **sensor health monitoring** and **a complete Auto Operation system**, it surpasses existing examples.


---

## 12. Implementation (Skeleton)

The executable skeleton of this system is implemented in this same repository. The complete structure, mapping of
requirements to code, and the run guide are in [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)
and the [`docs/`](docs/) folder.

Summary:

| Section | Path | Technology |
|---|---|---|
| Backend microservices | [`services/`](services/) | Python 3.11 + FastAPI |
| AI engine and models | [`ml/`](ml/) | NumPy/SciPy + scikit-learn (replaces CNN+LSTM with the same interface) |
| Dashboard | [`apps/dashboard/`](apps/dashboard/) | React + Vite + TypeScript (RTL) |
| Development infrastructure | [`docker-compose.yml`](docker-compose.yml) | PostgreSQL, InfluxDB, Kafka, MQTT, Grafana, MinIO |

Main services: `asset-registry` (asset hierarchy and full equipment↔sensor↔camera mapping),
`data-acquisition` (physical simulator of the complex + MQTT bridge), `signal-processing` (FFT/Wavelet,
feature extraction), `ai-engine` (detection of 16 faults), `prediction-rul` (RUL and 72-hour alert),
`sensor-health` (three-light green/yellow/red + measurement unit), `auto-operation` (5-level smart
operator + on/off control and standby swap with online optimization), `economics` (instantaneous profit and
savings in dollars for the manager), `alerting`, `reporting`, and `api-gateway`.

```bash
cp .env.example .env
make up        # bring up the whole stack
make train     # train the fault detection model and RUL estimator on synthetic data
make seed      # generate and load synthetic data (section 10)
make dashboard # run the frontend on http://localhost:5173
```
