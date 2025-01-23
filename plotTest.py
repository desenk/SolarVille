import pandas as pd
import matplotlib.pyplot as plt

 # List of specified household IDs
 household_ids = [
     "MAC000450", "MAC003252", "MAC003281", "MAC003305",
     "MAC003348", "MAC003394", "MAC003428", "MAC003553",
     "MAC003874", "MAC003863"
 ]

 # File path for household data
 file_path = "/home/pi/block_0.csv"
 # File path for solar output data
 solar_output_file_path = "/home/pi/SolarOutput.csv"

 # Load household data
 def load_household_data(file_path, household_ids):
     try:
         # Load the CSV file
         df = pd.read_csv(file_path, encoding='utf-8')  # If utf-8 fails, try 'latin1'
         # Standardize column names
         df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)

         household_column = 'lclid'
         timestamp_column = 'tstp'
         energy_column = 'energykwhhh'

         # Check if required columns exist
         required_columns = {household_column, timestamp_column, energy_column}
         if not required_columns.issubset(set(df.columns)):
             raise ValueError(f"Missing required columns: {required_columns - set(df.columns)}")

         # Filter data for specified households
         df = df[df[household_column].isin(household_ids)]

         # Convert timestamps to datetime type
         df[timestamp_column] = pd.to_datetime(df[timestamp_column], errors='coerce')

         # Filter data for June 1st to June 10th of 2013
         df = df[(df[timestamp_column].dt.year == 2013) & 
                 (df[timestamp_column].dt.month == 6) & 
                 (df[timestamp_column].dt.day >= 1) & 
                 (df[timestamp_column].dt.day <= 10)]

         # Set timestamp as index
         df = df.set_index(timestamp_column)
         return df
     except Exception as e:
         print(f"Failed to load data: {e}")
         return None

 # Plot energy usage for each household
 def plot_household_data(df, household_ids):
     plt.figure(figsize=(12, 6), constrained_layout=True)

     for household_id in household_ids:
         # Extract data for the specific household
         household_data = df[df["lclid"] == household_id]

         # Resample data to 30-minute intervals
         half_hour_data = household_data["energykwhhh"].resample("30T").sum().asfreq("30T")

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
         # Load solar output CSV file
         df = pd.read_csv(solar_output_file_path, encoding='utf-8')

         # Skip the first 3 columns and extract time and electricity columns
         df = df.iloc[:, 3:].copy()

         # Standardize column names
         df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)

         # Convert time column to datetime
         df['time'] = pd.to_datetime(df['time'], errors='coerce')

         # Filter data for June 1st to June 10th of 2013
         df = df[(df['time'].dt.year == 2013) & 
                 (df['time'].dt.month == 6) & 
                 (df['time'].dt.day >= 1) & 
                 (df['time'].dt.day <= 10)]

         # Set time as index
         df = df.set_index('time')
         return df
     except Exception as e:
         print(f"Failed to load solar output data: {e}")
         return None

 # Plot solar output data
 def plot_solar_output_data(df):
     plt.figure(figsize=(12, 6), constrained_layout=True)

     # Plot solar electricity output
     plt.plot(df.index, df['electricity'], label="Solar Panel Electricity Output", color='orange')

     # Configure the chart
     plt.title("Solar Panel Electricity Output (June 1 - June 10, 2013)")
     plt.xlabel("Date and Time")
     plt.ylabel("Electricity Output (kWh)")
     plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1))  # Place legend on the right
     plt.grid(True)
     plt.tight_layout()

 # Main function
 if __name__ == "__main__":
     # Load household data
     df_household = load_household_data(file_path, household_ids)
     if df_household is not None:
         # Plot the household data
         plot_household_data(df_household, household_ids)

     # Load solar output data
     df_solar = load_solar_output_data(solar_output_file_path)
     if df_solar is not None:
         # Plot the solar output data
         plot_solar_output_data(df_solar)

     # Show the plots
     plt.show()
