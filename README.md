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

## 🛠️ Installation
You need to download a dataset to run the `dataAnalysis.py` file on. You can download it from [here.](https://uoe-my.sharepoint.com/:x:/g/personal/s2288094_ed_ac_uk/EXgZsSNw8MxHp46RTw_X_n0BuPif69lbyKBb_PfBL7Lr8g?e=lzOABi) Save this on your computer and replace the existing path of `block_0.csv` in line 159 of `dataAnalysis.py` with your own path to the `block_0.csv` file. E.g `file_path = "/your/path/to/file/block_0.csv"`

You may have to install some python packages to run this file. These are 'pandas', 'numpy', 'matplotlib' and 'datetime' and you can use `pip install pandas numpy matplotlib datetime` to install them. It may be a good idea to set up a virtual python environment first so that there are no conflicts between packages.

To run the script, go to a terminal and naviagate to where the `dataAnalysis.py` file is located. Then run `python dataAnalysis.py --start_date 2012-10-13 --timescale 'd'`. You can change the date to another day in the data set and also use the 'd', 'w', 'm' and 'y' flags to change the timescale that is plotted.

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
