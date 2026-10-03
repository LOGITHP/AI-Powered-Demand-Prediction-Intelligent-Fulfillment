import pandas as pd
import numpy as np
import random
import os

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 1. Warehouse Configuration
warehouses = [
    {'warehouse_id': 'WH01', 'capacity': 'medium', 'efficiency_multiplier': 1.2, 'congestion_sensitivity': 1.0, 'base_equipment': 0.9},
    {'warehouse_id': 'WH02', 'capacity': 'large', 'efficiency_multiplier': 1.0, 'congestion_sensitivity': 0.8, 'base_equipment': 0.95},
    {'warehouse_id': 'WH03', 'capacity': 'small', 'efficiency_multiplier': 1.1, 'congestion_sensitivity': 1.5, 'base_equipment': 0.85},
    {'warehouse_id': 'WH04', 'capacity': 'large', 'efficiency_multiplier': 0.9, 'congestion_sensitivity': 0.9, 'base_equipment': 0.9},
    {'warehouse_id': 'WH05', 'capacity': 'medium', 'efficiency_multiplier': 1.0, 'congestion_sensitivity': 1.1, 'base_equipment': 0.88}
]

processes = ['RECEIVING', 'INSPECTION', 'PUTAWAY', 'PICKING', 'PACKING', 'LOADING']
skills = ['Beginner', 'Intermediate', 'Expert']

# Base productivity per process per worker per hour
base_productivity = {
    'RECEIVING': 200, # units/hour
    'INSPECTION': 150, # units/hour
    'PUTAWAY': 300, # units/hour
    'PICKING': 400, # items/hour
    'PACKING': 50, # orders/hour
    'LOADING': 100 # packages/hour
}

def generate_workers():
    workers = []
    for i in range(1, 501):
        wh = np.random.choice([w['warehouse_id'] for w in warehouses])
        skill = np.random.choice(skills, p=[0.3, 0.5, 0.2])
        exp = np.random.uniform(0.5, 10) if skill != 'Beginner' else np.random.uniform(0, 1)
        shift = np.random.choice([1, 2, 3])
        
        workers.append({
            'worker_id': f'W{i:04d}',
            'warehouse_id': wh,
            'skill_level': skill,
            'experience_years': exp,
            'shift': shift,
            'attendance_prob': np.random.uniform(0.85, 0.99)
        })
    return pd.DataFrame(workers)

def simulate_operations(workers_df):
    records = []
    dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
    
    # Pre-calculate warehouse maps
    wh_map = {w['warehouse_id']: w for w in warehouses}
    
    for current_date in dates:
        day_of_week = current_date.dayofweek
        # Weekend lower volume, mid-week higher
        dow_factor = 0.7 if day_of_week >= 5 else 1.0
        
        for wh_id, wh_info in wh_map.items():
            for shift in [1, 2, 3]:
                # Scheduled workers for this wh and shift
                shift_workers = workers_df[(workers_df['warehouse_id'] == wh_id) & (workers_df['shift'] == shift)]
                
                # Determine how many show up
                absent = 0
                for _, w in shift_workers.iterrows():
                    if random.random() > w['attendance_prob']:
                        absent += 1
                
                scheduled_workers = len(shift_workers)
                available_workers = scheduled_workers - absent
                
                if available_workers == 0:
                    available_workers = 1 # Avoid division by zero
                
                # Calculate average skill/exp of available workers (approximation)
                avg_exp = shift_workers['experience_years'].mean() if not shift_workers.empty else 1.0
                skill_scores = {'Beginner': 0.8, 'Intermediate': 1.0, 'Expert': 1.2}
                avg_skill = shift_workers['skill_level'].map(skill_scores).mean() if not shift_workers.empty else 1.0
                
                # Global equipment availability and warehouse utilization for the shift
                equipment_available = np.clip(np.random.normal(wh_info['base_equipment'], 0.05), 0.5, 1.0)
                warehouse_utilization = np.clip(np.random.normal(0.7, 0.15), 0.3, 0.99)
                
                for process in processes:
                    # Distribute available workers among processes (simplified: assume even distribution + some randomness)
                    process_workers = max(1, int(available_workers / len(processes)))
                    
                    # Generate workload
                    base_vol = np.random.normal(5000, 1000)
                    # Occasional spikes
                    spike_factor = 1.8 if random.random() < 0.05 else 1.0
                    
                    workload = int(base_vol * dow_factor * wh_info['efficiency_multiplier'] * spike_factor)
                    if workload < 100: workload = 100
                    
                    # Other metrics based on process
                    if process == 'PACKING':
                        num_orders = int(workload / 5) # avg 5 items per order
                        workload_qty = num_orders
                    elif process == 'LOADING':
                        workload_qty = int(workload / 2) # avg 2 items per package
                        num_orders = workload_qty
                    else:
                        workload_qty = workload
                        num_orders = int(workload / 5)
                        
                    num_items = workload
                    num_skus = int(workload * np.random.uniform(0.1, 0.3))
                    current_queue = int(workload_qty * np.random.uniform(0.05, 0.3))
                    
                    # Task complexity
                    task_complexity = np.random.uniform(0.8, 1.3)
                    distance_factor = np.random.uniform(0.8, 1.2)
                    
                    # Effective productivity calculation
                    # Base * WH efficiency * Avg Skill * Equipment * Complexity
                    effective_prod = base_productivity[process] * wh_info['efficiency_multiplier'] * avg_skill * equipment_available / task_complexity
                    
                    # Congestion impact on productivity
                    if warehouse_utilization > 0.85:
                        congestion_penalty = 1 - (warehouse_utilization - 0.85) * wh_info['congestion_sensitivity']
                        effective_prod *= max(0.5, congestion_penalty)
                        
                    # Calculate Labels
                    # Label 1: Required workers (working time per shift is approx 7.5 hours)
                    productive_hours = 7.5
                    capacity_per_worker = effective_prod * productive_hours
                    required_workers = int(np.ceil(workload_qty / capacity_per_worker))
                    
                    # Label 2: Processing time (minutes)
                    # Actual time based on assigned process workers
                    total_effective_capacity_per_hour = effective_prod * process_workers
                    processing_time_hours = workload_qty / total_effective_capacity_per_hour
                    processing_time_minutes = int(processing_time_hours * 60)
                    
                    # Adjust processing time based on queue
                    processing_time_minutes += int((current_queue / total_effective_capacity_per_hour) * 60)
                    
                    # Label 3: Delay status
                    # Service time is assume 8 hours (480 mins)
                    service_time_mins = 480
                    delay_status = 1 if processing_time_minutes > service_time_mins else 0
                    
                    # Label 4: Congestion status
                    # Congestion if utilization > 90% or queue > 50% of shift capacity
                    shift_capacity = total_effective_capacity_per_hour * productive_hours
                    congestion_status = 1 if (warehouse_utilization > 0.9) or (current_queue > 0.5 * shift_capacity) else 0
                    
                    # Label 5: Worker productivity (actual output per worker hour)
                    worker_productivity = total_effective_capacity_per_hour / process_workers
                    
                    record = {
                        'date': current_date,
                        'warehouse_id': wh_id,
                        'shift': shift,
                        'process_type': process,
                        'zone_id': f"{wh_id}_{process[:3]}",
                        'workload_quantity': workload_qty,
                        'number_of_orders': num_orders,
                        'number_of_items': num_items,
                        'number_of_skus': num_skus,
                        'scheduled_workers': int(scheduled_workers / len(processes)), # apportioned
                        'absent_workers': int(absent / len(processes)),
                        'available_workers': process_workers,
                        'average_worker_experience': avg_exp,
                        'average_worker_skill': avg_skill,
                        'equipment_available': equipment_available,
                        'equipment_utilization': equipment_available * np.random.uniform(0.7, 0.95),
                        'current_queue': current_queue,
                        'warehouse_utilization': warehouse_utilization,
                        'historical_productivity': base_productivity[process],
                        'distance_factor': distance_factor,
                        'task_complexity': task_complexity,
                        'required_workers': required_workers,
                        'processing_time_minutes': processing_time_minutes,
                        'delay_status': delay_status,
                        'congestion_status': congestion_status,
                        'worker_productivity': worker_productivity
                    }
                    records.append(record)
                    
    df = pd.DataFrame(records)
    df.sort_values(by=['date', 'warehouse_id', 'shift', 'process_type'], inplace=True)
    return df

def generate_data_dictionary():
    dict_data = [
        {'column_name': 'date', 'data_type': 'datetime', 'description': 'Date of operations', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'warehouse_id', 'data_type': 'string', 'description': 'Warehouse identifier', 'feature_or_label': 'feature', 'allowed_values': 'WH01-WH05'},
        {'column_name': 'shift', 'data_type': 'int', 'description': 'Work shift', 'feature_or_label': 'feature', 'allowed_values': '1, 2, 3'},
        {'column_name': 'process_type', 'data_type': 'string', 'description': 'Warehouse process', 'feature_or_label': 'feature', 'allowed_values': 'RECEIVING, INSPECTION, PUTAWAY, PICKING, PACKING, LOADING'},
        {'column_name': 'zone_id', 'data_type': 'string', 'description': 'Area where process occurs', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'workload_quantity', 'data_type': 'int', 'description': 'Primary workload volume', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'number_of_orders', 'data_type': 'int', 'description': 'Number of orders involved', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'number_of_items', 'data_type': 'int', 'description': 'Total items involved', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'number_of_skus', 'data_type': 'int', 'description': 'Unique SKUs', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'scheduled_workers', 'data_type': 'int', 'description': 'Workers scheduled for process', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'absent_workers', 'data_type': 'int', 'description': 'Workers absent for process', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'available_workers', 'data_type': 'int', 'description': 'Workers available for process', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'average_worker_experience', 'data_type': 'float', 'description': 'Avg years of exp', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'average_worker_skill', 'data_type': 'float', 'description': 'Avg skill score', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'equipment_available', 'data_type': 'float', 'description': 'Ratio of equipment working', 'feature_or_label': 'feature', 'allowed_values': '0.0 - 1.0'},
        {'column_name': 'equipment_utilization', 'data_type': 'float', 'description': 'Usage rate of equipment', 'feature_or_label': 'feature', 'allowed_values': '0.0 - 1.0'},
        {'column_name': 'current_queue', 'data_type': 'int', 'description': 'Backlog before shift', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'warehouse_utilization', 'data_type': 'float', 'description': 'Storage fill rate', 'feature_or_label': 'feature', 'allowed_values': '0.0 - 1.0'},
        {'column_name': 'historical_productivity', 'data_type': 'float', 'description': 'Base items/hr', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'distance_factor', 'data_type': 'float', 'description': 'Travel distance multiplier', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'task_complexity', 'data_type': 'float', 'description': 'Difficulty of tasks', 'feature_or_label': 'feature', 'allowed_values': ''},
        {'column_name': 'required_workers', 'data_type': 'int', 'description': 'Optimal workers needed', 'feature_or_label': 'label', 'allowed_values': ''},
        {'column_name': 'processing_time_minutes', 'data_type': 'int', 'description': 'Actual mins taken', 'feature_or_label': 'label', 'allowed_values': ''},
        {'column_name': 'delay_status', 'data_type': 'int', 'description': 'If process delayed', 'feature_or_label': 'label', 'allowed_values': '0, 1'},
        {'column_name': 'congestion_status', 'data_type': 'int', 'description': 'If area congested', 'feature_or_label': 'label', 'allowed_values': '0, 1'},
        {'column_name': 'worker_productivity', 'data_type': 'float', 'description': 'Actual throughput/hr', 'feature_or_label': 'label', 'allowed_values': ''}
    ]
    pd.DataFrame(dict_data).to_csv(os.path.join(DATA_DIR, 'data_dictionary.csv'), index=False)

def main():
    print("Generating workers...")
    workers_df = generate_workers()
    
    print("Simulating warehouse operations...")
    ops_df = simulate_operations(workers_df)
    
    # Save main dataset
    ops_df.to_csv(os.path.join(DATA_DIR, 'warehouse_operations.csv'), index=False)
    print(f"Generated {len(ops_df)} records.")
    
    # Chronological Split: 70% / 15% / 15%
    unique_dates = ops_df['date'].unique()
    n_dates = len(unique_dates)
    
    train_split = int(n_dates * 0.7)
    val_split = int(n_dates * 0.85)
    
    train_dates = unique_dates[:train_split]
    val_dates = unique_dates[train_split:val_split]
    test_dates = unique_dates[val_split:]
    
    train_df = ops_df[ops_df['date'].isin(train_dates)]
    val_df = ops_df[ops_df['date'].isin(val_dates)]
    test_df = ops_df[ops_df['date'].isin(test_dates)]
    
    train_df.to_csv(os.path.join(DATA_DIR, 'train.csv'), index=False)
    val_df.to_csv(os.path.join(DATA_DIR, 'validation.csv'), index=False)
    test_df.to_csv(os.path.join(DATA_DIR, 'test.csv'), index=False)
    
    print(f"Train/Val/Test splits saved. Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # Save data dictionary
    generate_data_dictionary()
    print("Data dictionary saved.")

if __name__ == '__main__':
    main()
