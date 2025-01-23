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
