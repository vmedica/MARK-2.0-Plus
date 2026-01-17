"""Simple data processing script - No ML."""
import json
import csv

def load_data(filename):
    """Load data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def save_csv(data, filename):
    """Save data to CSV file."""
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

if __name__ == "__main__":
    data = load_data('input.json')
    save_csv(data, 'output.csv')
    print("Processing complete!")
