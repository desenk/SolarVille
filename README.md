# 🌞 SolarVille: Table-top Smart Grid Demo 🌩️

## 📄 Summary
Welcome to SolarVille! The future of our grid  – packed into a sleek table-top demo using Raspberry Pis, rechargeable batteries, and mini solar panels. Dive into the world of energy management, where consumption meets innovation. 🚀

## 🤖 Overview
SolarVille isn't just any demo; it's a power-packed simulation designed to mimic real-life scenarios of a smart grid. Armed with Raspberry Pis acting as consumers and prosumers, we delve into the dynamic world of electricity that's not just used but also generated and shared. Here’s the cool part:

- You control 🕹️ real-time generation with mini solar panels.
- You monitor the juice 📊 (state of charge) in our lithium-ion batteries.
- You rule the grid, directing power where it's needed or trading it with your neighbours!

### ⛈️ Plus, Weather Modes! 🌞
Experience how weather messes with energy. Normal day? Heat wave? Stormy skies? Each scenario uniquely affects power generation and demand. Buckle up, as SolarVille brings you the climate challenge!

## 🎯 Goals
- **Enlighten**: Learn the grit of grid management.
- **Demonstrate**: See real weather impacts on solar power.
- **Simulate**: Watch and manage as the sun rises and sets and storms roll in.

## Prerequisites
- Python 3.11
- Required Python packages (see `requirements.txt` and `requirements-pi.txt`)
- Raspberry Pi 4

## Setup Instructions

### Step 1: Clone the Repository
```sh
git clone https://github.com/your-repo/SolarVille.git
cd SolarVille
```
### Step 2: Set up the Virtual Environment
```sh
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Step 3: Install Dependencies
**For Mac/Linux:**
```sh
pip install -r requirements.txt
```
**For Raspberry Pi:**
```sh
pip install -r requirements-pi.txt
```

## Running the Simulation

### Step 1: Prepare the Data

Ensure you have the CSV file containing energy data. The CSV file should be structured correctly and located in the project directory. You can download the sample data from [here](https://www.dropbox.com/scl/fi/q0bnffnh7ri5hrr19lzln/block_0.csv?rlkey=q57lpbt8csgphdeqta0m2n2yl&st=o1uxz728&dl=0).

### Step 2: Run the Simulation
```sh
python main.py --file_path <path_to_csv> --household <household_id> --start_date <start_date> --timescale <timescale>
```
- <path_to_csv>: Path to your energy data CSV file
- <household_id>: Household ID to filter data
- <start_date>: Start date for the simulation (format: YYYY-MM-DD)
- <timescale>: Timescale for the simulation (‘d’ for day, ‘w’ for week, ‘m’ for month, ‘y’ for year)

**Example:**
```sh
python main.py --file_path data/block_0.csv --household MAC000002 --start_date 2012-10-13 --timescale 'd'
```

## Additional Information

**Raspberry Pi Specific Setup**

For Raspberry Pi, ensure the correct hardware connections, making sure to adjust the GPIO pins in the code to your requirements. Install additional libraries specified in requirements-pi.txt.

## 🔄 Usage
Get your hands on the controls with our super user-friendly guide. Adjust the weather, watch energy flow, tweak setups – all in real-time!

## 💡 Contribute
Got ideas? Enhancements? We’re all ears! 💬 Here’s how you can contribute:

- *Tinker with Hardware*: Got a knack for gadgets? Help us enhance our setup.
- *Boost the Software*: Coders welcome – let’s make SolarVille smarter.
- *Expand Knowledge*: Share resources, teach others, be a grid guru.

## 📜 Licensing
Details on how you can use and share SolarVille are on the way.

## ☎️ Contact
Questions? Suggestions? Reach out to us at desen.kirli@ed.ac.uk

## 🙌 Acknowledgements
Shoutout to Jack Scott, Arif Akanda and Chun Gou making SolarVille possible – you’re awesome!

### 🚀 Join us in this electrifying adventure as we power through simulations and harness the sun in SolarVille! ⚡🌍# SolarVille
