import pandas as pd
import matplotlib.pyplot as plt

# List of specified household IDs
household_ids = [
    "MAC000450", "MAC003252", "MAC003281", "MAC003305",
    "MAC003348", "MAC003394", "MAC003428", "MAC003553",
    "MAC003874", "MAC003863"
]

# File paths
file_path = "/home/pi/block_0.csv"
solar_output_file_path = "/home/pi/SolarOutput.csv"

# Load household data
def load_household_data(file_path, household_ids):
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)

        required_columns = {'lclid', 'tstp', 'energykwhhh'}
        if not required_columns.issubset(set(df.columns)):
            raise ValueError(f"Missing required columns: {required_columns - set(df.columns)}")

        df = df[df['lclid'].isin(household_ids)]
        df['tstp'] = pd.to_datetime(df['tstp'], errors='coerce')
        df = df[(df['tstp'].dt.year == 2013) & (df['tstp'].dt.month == 6) & (df['tstp'].dt.day <= 10)]
        df = df.set_index('tstp')
        return df
    except Exception as e:
        print(f"Error loading household data from {file_path}: {e}")
        return None

# Plot energy usage for each household
def plot_household_data(df, household_ids):
    if df is None or df.empty:
        print("No household data available for plotting.")
        return

    plt.figure(figsize=(12, 6), constrained_layout=True)

    for household_id in household_ids:
        # Extract data for the specific household
        household_data = df[df["lclid"] == household_id].copy()

        # Ensure energykwhhh column contains valid numeric data
        household_data["energykwhhh"] = pd.to_numeric(household_data["energykwhhh"], errors="coerce")
        household_data = household_data.dropna(subset=["energykwhhh"])

        # Resample data to 30-minute intervals
        household_data = household_data.set_index(household_data.index)  # Ensure proper index
        half_hour_data = household_data["energykwhhh"].resample("30min").sum().asfreq("30min")

        # Plot the data for each household
        plt.plot(half_hour_data.index, half_hour_data.values, label=f"Household {household_id}")

    # Configure the chart
    plt.title("Household Energy Usage (June 1 - June 10, 2013) at Half-Hour Intervals")
    plt.xlabel("Date and Time")
    plt.ylabel("Energy Usage (kWh)")
    plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1))  # Place legend on the right
    plt.grid(True)
    plt.tight_layout()

# Load solar output data
def load_solar_output_data(solar_output_file_path):
    try:
        df = pd.read_csv(solar_output_file_path, encoding='utf-8')
        df = df.iloc[:, 3:]
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df[(df['time'].dt.year == 2013) & (df['time'].dt.month == 6) & (df['time'].dt.day <= 10)]
        df = df.set_index('time')
        return df
    except Exception as e:
        print(f"Error loading solar output data from {solar_output_file_path}: {e}")
        return None

# Plot solar output data
def plot_solar_output_data(df):
    if df is None or df.empty:
        print("No solar output data available for plotting.")
        return

    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['electricity'], label="Solar Panel Electricity Output", color='orange')
    plt.title("Solar Panel Electricity Output (June 1 - June 10, 2013)")
    plt.xlabel("Date and Time")
    plt.ylabel("Electricity Output (kWh)")
    plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
    plt.grid(True)

# Main function
if __name__ == "__main__":
    df_household = load_household_data(file_path, household_ids)
    plot_household_data(df_household, household_ids)

    df_solar = load_solar_output_data(solar_output_file_path)
    plot_solar_output_data(df_solar)

    plt.tight_layout()
    plt.show()
