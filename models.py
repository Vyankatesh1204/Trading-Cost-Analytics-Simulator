#model.py 

from sklearn.linear_model import LogisticRegression
import joblib
import os

class ModelManager:
    """
    Manages training, loading, and prediction for the Maker-Taker classification model.
    """

    def __init__(self, model_path="maker_taker_model.pkl", retrain_if_missing=False):
        self.model_path = model_path
        self.maker_taker_model = None

        if os.path.exists(self.model_path):
            self._load_model()
        elif retrain_if_missing:
            self.train_and_save_model()
        else:
            raise FileNotFoundError(f"Model file not found: {self.model_path}. "
                                    f"Set retrain_if_missing=True to train a mock model.")

    def _load_model(self):
        """
        Load the ML model from disk.
        """
        try:
            self.maker_taker_model = joblib.load(self.model_path)
            print("✅ Maker-Taker model loaded from disk.")
        except Exception as e:
            raise RuntimeError(f"❌ Error loading model: {e}")

    def train_and_save_model(self):
        """
        Train a Logistic Regression model on mock data and save it.
        """
        # Mock training data — replace this with real historical trade features
        X_train = [[0.8], [1.2], [0.5], [1.5], [0.6]]
        y_train = [1, 1, 0, 1, 0]  # 1 = maker, 0 = taker

        self.maker_taker_model = LogisticRegression()
        self.maker_taker_model.fit(X_train, y_train)
        joblib.dump(self.maker_taker_model, self.model_path)
        print("🧠 Model trained on mock data and saved to disk.")

    def predict_maker_taker(self, ratio):
        """
        Predict whether a given ratio belongs to a maker (1) or taker (0) trade.

        :param ratio: A float value (e.g., slippage/execution price).
        :return: 1 for maker, 0 for taker, or -1 on error.
        """
        if self.maker_taker_model:
            try:
                prediction = self.maker_taker_model.predict([[ratio]])
                return int(prediction[0])
            except Exception as e:
                print(f"[⚠️ Prediction error] {e}")
                return -1
        else:
            print("⚠️ No model loaded.")
            return -1
