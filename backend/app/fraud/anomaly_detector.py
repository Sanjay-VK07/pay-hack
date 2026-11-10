import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from app.models.models import Transaction, CustomerAccount

class AnomalyDetector:
    """
    Scikit-learn Isolation Forest baseline anomaly detector for behavioral transaction deviations.
    Trained on tabular numerical features:
    [amount, customer_account_age, device_sharing_count, failed_attempt_count]
    """
    def __init__(self, db: Session):
        self.db = db
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.15,
            random_state=42
        )
        self.is_fitted = False

    def _extract_features(self, transactions: List[Transaction]) -> np.ndarray:
        features = []
        for txn in transactions:
            acc_age = 30
            if txn.customer:
                acc_age = txn.customer.account_age_days
            
            # Simple numerical representation
            f_amount = float(txn.amount)
            f_acc_age = float(acc_age)
            f_is_failed = 1.0 if txn.payment_status == "FAILED" else 0.0
            f_is_high_risk = 1.0 if txn.risk_category in ("HIGH", "CRITICAL") else 0.0

            features.append([f_amount, f_acc_age, f_is_failed, f_is_high_risk])

        return np.array(features) if features else np.empty((0, 4))

    def fit_baseline(self) -> bool:
        txns = self.db.query(Transaction).all()
        if len(txns) < 5:
            return False
        
        X = self._extract_features(txns)
        if len(X) < 5:
            return False

        self.model.fit(X)
        self.is_fitted = True
        return True

    def score_transaction(self, transaction: Transaction) -> float:
        """
        Returns normalized anomaly score between 0.0 (normal) and 1.0 (highly anomalous).
        """
        if not self.is_fitted:
            success = self.fit_baseline()
            if not success:
                return 0.15  # Default baseline when insufficient training samples

        acc_age = 30
        if transaction.customer:
            acc_age = transaction.customer.account_age_days

        x = np.array([[
            float(transaction.amount),
            float(acc_age),
            1.0 if transaction.payment_status == "FAILED" else 0.0,
            1.0 if transaction.risk_category in ("HIGH", "CRITICAL") else 0.0
        ]])

        try:
            # decision_function yields lower scores for abnormal points
            raw_score = self.model.decision_function(x)[0]
            # Map raw score roughly [-0.5, 0.5] to [1.0, 0.0]
            normalized = float(np.clip(0.5 - raw_score, 0.0, 1.0))
            return round(normalized, 3)
        except Exception:
            return 0.2
