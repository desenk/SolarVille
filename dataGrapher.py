import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# Read the CSV file
df = pd.read_csv('Solar battery data Aug 02.csv', parse_dates=['Timestamp'])

# Set the Timestamp as the index
df.set_index('Timestamp', inplace=True)

# Create a figure with subplots
fig, axs = plt.subplots(3, 1, figsize=(12, 15), sharex=True)

# Plot Solar and Battery Bus Voltage
axs[0].plot(df.index, df['Solar Bus Voltage (V)'], label='Solar')
axs[0].plot(df.index, df['Battery Bus Voltage (V)'], label='Battery')
axs[0].set_ylabel('Bus Voltage (V)')
axs[0].legend()
axs[0].set_title('Bus Voltage over Time')

# Plot Solar and Battery Current
axs[1].plot(df.index, df['Solar Current (A)'], label='Solar')
axs[1].plot(df.index, df['Battery Current (A)'], label='Battery')
axs[1].set_ylabel('Current (A)')
axs[1].legend()
axs[1].set_title('Current over Time')

# Plot Solar and Battery Power
axs[2].plot(df.index, df['Solar Power (mW)'], label='Solar')
axs[2].plot(df.index, df['Battery Power (mW)'], label='Battery')
axs[2].set_ylabel('Power (mW)')
axs[2].legend()
axs[2].set_title('Power over Time')

# Format x-axis to show time
for ax in axs:
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

# Rotate and align the tick labels so they look better
plt.gcf().autofmt_xdate()

# Add a title to the entire figure
fig.suptitle('Solar Panel and Battery Performance', fontsize=16)

# Adjust the layout and display the plot
plt.tight_layout()
plt.show()

# Save the figure
plt.savefig('solar_battery_performance.png', dpi=300, bbox_inches='tight')