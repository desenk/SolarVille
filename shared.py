import pandas as pd # type: ignore
import logging

class SimulationState:
    def __init__(self):
        self.df = None

    def get_local_state(self):
        return {
            'timestamp': self.df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            'balance': float(self.df.loc[self.df.index[-1], 'balance']),
            'battery_charge': float(self.df.loc[self.df.index[-1], 'battery_charge']),
            'currency': float(self.df.loc[self.df.index[-1], 'currency'])
        }

    def resynchronize(self, peer_state):
        current_index = self.df.index.get_loc(pd.to_datetime(peer_state['timestamp']))
        self.df.loc[self.df.index[current_index], 'balance'] = peer_state['balance']
        self.df.loc[self.df.index[current_index], 'battery_charge'] = peer_state['battery_charge']
        self.df.loc[self.df.index[current_index], 'currency'] = peer_state['currency']
        logging.info(f"Resynchronized at {peer_state['timestamp']}")

sim_state = SimulationState()