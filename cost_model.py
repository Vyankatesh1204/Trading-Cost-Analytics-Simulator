#cost_model.py
import pickle
import pandas as pd  # Import pandas
import os

class CostRegressionModel:
    def __init__(self, model_path='cost_model.pkl'):
        """
        Initialize the model by loading a trained regression model from a pickle file.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ Model file '{model_path}' not found. Please train and save the model first.")
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

    def predict_cost(self, quantity, price, side, volatility, time_of_day):
        """
        Predict the transaction cost for a given trade.

        Parameters:
        - quantity (float): number of units traded
        - price (float): price per unit
        - side (str): "Buy" or "Sell"
        - volatility (float): market volatility
        - time_of_day (float): e.g., 0 (market open) to 1 (close)

        Returns:
        - float: predicted transaction cost
        """
        if self.model is None:
            raise ValueError("Model is not loaded.")
        
        side_encoded = 1 if side.lower() == "buy" else 0

        # Create a DataFrame with feature names matching training data
        features = pd.DataFrame([[quantity, price, side_encoded, volatility, time_of_day]],
                                columns=['quantity', 'price', 'side', 'volatility', 'time_of_day'])
        
        predicted_cost = self.model.predict(features)
        return predicted_cost[0]
