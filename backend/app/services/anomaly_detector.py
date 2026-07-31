import os
import pickle
from typing import Any

from river import anomaly #type:ignore


class BehavioralAnomalyDetector:
    """Incremental Online ML Model for scoring continuous biometric behavior.

    Maintains separate HalfSpaceTrees (HST) instances for keystroke dynamics
    and mouse movement dynamics to prevent feature space corruption across signal types.
    """

    def __init__(self, user_id: str, model_dir: str = "app/models/saved_models"):
        self.user_id = user_id
        self.model_dir = model_dir

        self.ks_model_path = os.path.join(self.model_dir, f"{self.user_id}_keystroke_hst.pkl")
        self.mouse_model_path = os.path.join(self.model_dir, f"{self.user_id}_mouse_hst.pkl")

        self.keystroke_model = self._load_or_create_model(self.ks_model_path)
        self.mouse_model = self._load_or_create_model(self.mouse_model_path)

    def _load_or_create_model(self, file_path: str) -> anomaly.HalfSpaceTrees:
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    print(f"Loaded existing ML model from: {file_path}")
                    return pickle.load(f)
            except Exception as e:
                print(f"Failed to load model at {file_path}, creating fresh instance: {e}")

        return anomaly.HalfSpaceTrees(
            n_trees=25,
            height=15,
            window_size=100,
            seed=42
        )

    def predict_and_update(self, features: dict[str, Any]) -> float | None:
        feature_type = features.get("feature_type")

        if feature_type == "keystroke_aggregate":
            numeric_features = {
                "hold_time": features.get("hold_time", 0.0),
                "flight_time": features.get("flight_time", 0.0),
                "mean_hold_time": features.get("mean_hold_time", 0.0),
                "std_hold_time": features.get("std_hold_time", 0.0),
                "mean_flight_time": features.get("mean_flight_time", 0.0),
                "std_flight_time": features.get("std_flight_time", 0.0),
            }
            return self._score_and_learn(self.keystroke_model, numeric_features)

        elif feature_type == "mouse_move_aggregate":
            numeric_features = {
                "velocity": features.get("velocity", 0.0),
                "acceleration": features.get("acceleration", 0.0),
                "jerk": features.get("jerk", 0.0),
                "mean_velocity": features.get("mean_velocity", 0.0),
            }
            return self._score_and_learn(self.mouse_model, numeric_features)

        return None

    def _score_and_learn(self, model: anomaly.HalfSpaceTrees, features: dict[str, float]) -> float:
        score: float = model.score_one(features)
        model.learn_one(features)
        return min(max(float(score), 0.0), 1.0)

    def save_models(self) -> None:
        os.makedirs(self.model_dir, exist_ok=True)
        try:
            with open(self.ks_model_path, "wb") as f:
                pickle.dump(self.keystroke_model, f)
            with open(self.mouse_model_path, "wb") as f:
                pickle.dump(self.mouse_model, f)
            print(f"Persisted ML models for user: {self.user_id}")
        except Exception as e:
            print(f"Failed to persist models for {self.user_id}: {e}")