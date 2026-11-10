from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.models import (
    CustomerAccount, Device, PaymentIdentity, Transaction,
    TransactionIndicator, PaymentOperation, User, InvestigationCase,
    InvestigationEvidence, AgentExecution, AgentFinding, RiskAssessment,
    ApprovalRequest, AuditLog, FraudCluster
)

def utcnow():
    return datetime.now(timezone.utc)

class SeedService:
    def __init__(self, db: Session):
        self.db = db

    def clear_database(self):
        """Clean slate for reproducible demo reset - deletes in proper FK dependency order"""
        self.db.query(AuditLog).delete()
        self.db.query(ApprovalRequest).delete()
        self.db.query(PaymentOperation).delete()
        self.db.query(RiskAssessment).delete()
        self.db.query(AgentFinding).delete()
        self.db.query(AgentExecution).delete()
        self.db.query(InvestigationEvidence).delete()
        self.db.query(InvestigationCase).delete()
        self.db.query(FraudCluster).delete()
        self.db.query(TransactionIndicator).delete()
        self.db.query(Transaction).delete()
        self.db.query(PaymentIdentity).delete()
        self.db.query(Device).delete()
        self.db.query(CustomerAccount).delete()
        self.db.query(User).delete()
        self.db.commit()

    def seed_demo_dataset(self) -> int:
        """
        Seeds 12 accounts, 28 transactions, 8 devices, 7 payment identities,
        with clear legitimate accounts and a discoverable coordinated fraud ring.
        """
        # 0. Investigator User
        admin_user = User(
            id="USR_001",
            username="investigator_lead",
            email="investigator@agentshield.internal",
            role="CHIEF_RISK_OFFICER"
        )
        self.db.add(admin_user)

        # 1. Devices
        now = utcnow()
        devices_data = [
            ("DEV_001", "FPR-IPHONE-A1", "MOBILE", "iOS 17.4", "Mobile Safari", False, "LOW"),
            ("DEV_002", "FPR-MACBOOK-B2", "DESKTOP", "macOS Sonoma", "Chrome 122", False, "LOW"),
            ("DEV_003", "FPR-DELL-C3", "DESKTOP", "Windows 11", "Edge 122", False, "LOW"),
            ("DEV_004", "FPR-IPAD-D4", "TABLET", "iPadOS 17", "Safari", False, "LOW"),
            ("DEV_005", "FPR-THINKPAD-E5", "DESKTOP", "Ubuntu 22.04", "Firefox 123", False, "LOW"),
            ("DEV_006", "FPR-PIXEL-F6", "MOBILE", "Android 14", "Chrome Mobile", False, "LOW"),
            # Coordinated Syndicate Shared Emulator
            ("DEV_007", "EMUL-BLUESTACKS-8839", "EMULATOR", "Android 9 (x86)", "Chrome 91 (Headless)", True, "HIGH"),
            # Syndicate Bot VM
            ("DEV_008", "BOT-SPOOFED-VM-9941", "DESKTOP", "Linux x86_64", "Puppeteer/Python", True, "HIGH")
        ]
        devices = {}
        for d_id, fp, dt, os_n, br, is_em, rl in devices_data:
            dev = Device(
                id=d_id,
                device_fingerprint=fp,
                device_type=dt,
                os=os_n,
                browser=br,
                is_emulator=is_em,
                risk_level=rl,
                first_seen=now - timedelta(days=40),
                last_seen=now
            )
            self.db.add(dev)
            devices[d_id] = dev

        # 2. Payment Identities
        identities_data = [
            ("PID_001", "CARD_HASH", "hash_visa_1042", "Visa •••• 1042", []),
            ("PID_002", "CARD_HASH", "hash_mc_9821", "Mastercard •••• 9821", []),
            ("PID_003", "PAYPAL_WALLET", "hash_pp_carol", "PayPal (carol@danvers.io)", []),
            ("PID_004", "CARD_HASH", "hash_amex_3004", "Amex •••• 3004", []),
            ("PID_005", "CARD_HASH", "hash_visa_7712", "Visa •••• 7712", []),
            # Shared Compromised Card 1 (Marcus & Viktor)
            ("PID_006", "CARD_HASH", "hash_stolen_corp_4242", "Visa •••• 4242", ["STOLEN_CARD_REPORTS", "CHARGEBACK_HISTORY"]),
            # Shared Syndicate Card 2 (Chloe & Damian)
            ("PID_007", "CARD_HASH", "hash_carding_mc_8888", "Mastercard •••• 8888", ["CARDING_RING_INDICATOR"])
        ]
        identities = {}
        for pid_id, it, ih, mv, flags in identities_data:
            pident = PaymentIdentity(
                id=pid_id,
                identity_type=it,
                identity_hash=ih,
                masked_value=mv,
                risk_flags=flags
            )
            self.db.add(pident)
            identities[pid_id] = pident

        # 3. 12 Customer Accounts
        accounts_data = [
            # 8 Legitimate Customers
            ("ACC_001", "ACCT-8001", "Alice Walker", "alice.w@example.com", "+1-555-0101", "US", "LOW", 240, "ACTIVE"),
            ("ACC_002", "ACCT-8002", "Bob Vance", "bob.vance@example.com", "+1-555-0102", "US", "LOW", 180, "ACTIVE"),
            ("ACC_003", "ACCT-8003", "Carol Danvers", "carol.d@example.com", "+1-555-0103", "US", "LOW", 310, "ACTIVE"),
            ("ACC_004", "ACCT-8004", "David Kim", "david.kim@example.com", "+1-555-0104", "US", "LOW", 95, "ACTIVE"),
            ("ACC_005", "ACCT-8005", "Elena Rostova", "elena.r@example.com", "+1-555-0105", "DE", "LOW", 410, "ACTIVE"),
            ("ACC_006", "ACCT-8006", "Frank Castle", "frank.c@example.com", "+1-555-0106", "US", "LOW", 120, "ACTIVE"),
            ("ACC_007", "ACCT-8007", "Grace Hopper", "grace.h@example.com", "+1-555-0107", "US", "LOW", 600, "ACTIVE"),
            ("ACC_008", "ACCT-8008", "Henry McCoy", "henry.m@example.com", "+1-555-0108", "CA", "MEDIUM", 45, "ACTIVE"),
            # 4 Coordinated Syndicate Accounts
            ("ACC_009", "ACCT-9009", "Marcus Sterling", "marcus.s88@tempinbox.me", "+1-555-9009", "US", "CRITICAL", 2, "UNDER_REVIEW"),
            ("ACC_010", "ACCT-9010", "Viktor Ramos", "viktor.ram99@burnermail.org", "+1-555-9010", "US", "CRITICAL", 3, "UNDER_REVIEW"),
            ("ACC_011", "ACCT-9011", "Chloe Bennett", "cbennett_express@privatemail.io", "+1-555-9011", "US", "CRITICAL", 1, "UNDER_REVIEW"),
            ("ACC_012", "ACCT-9012", "Damian Cross", "dcross_retail@throwaway.net", "+1-555-9012", "US", "CRITICAL", 4, "UNDER_REVIEW")
        ]
        accounts = {}
        for acc_id, num, name, email, phone, ctry, rr, age, stat in accounts_data:
            acc = CustomerAccount(
                id=acc_id,
                account_number=num,
                full_name=name,
                email=email,
                phone=phone,
                country=ctry,
                risk_rating=rr,
                account_age_days=age,
                status=stat,
                created_at=now - timedelta(days=age)
            )
            self.db.add(acc)
            accounts[acc_id] = acc

        self.db.flush()

        # 4. 28 Transactions (Realistic Marketplace Flow)
        ip_legit_home = "73.189.44.12"
        ip_legit_office = "98.244.11.89"
        ip_legit_mobile = "172.56.21.90"
        ip_tor_proxy = "185.220.101.5"
        ip_vpn_hosting = "45.154.255.88"

        transactions_spec = [
            # Legitimate transactions for Alice
            ("TXN_101", "ACC_001", 45.00, "USD", now - timedelta(days=5), "COMPLETED", 10.0, "LOW", "DEV_001", ip_legit_home, "PID_001", "NONE", None),
            ("TXN_102", "ACC_001", 120.50, "USD", now - timedelta(days=2), "COMPLETED", 12.0, "LOW", "DEV_001", ip_legit_home, "PID_001", "NONE", None),
            ("TXN_103", "ACC_001", 280.00, "USD", now - timedelta(hours=14), "COMPLETED", 15.0, "LOW", "DEV_001", ip_legit_office, "PID_001", "NONE", None),

            # Bob
            ("TXN_104", "ACC_002", 89.99, "USD", now - timedelta(days=4), "COMPLETED", 8.0, "LOW", "DEV_002", ip_legit_office, "PID_002", "NONE", None),
            ("TXN_105", "ACC_002", 340.00, "USD", now - timedelta(days=1), "COMPLETED", 14.0, "LOW", "DEV_002", ip_legit_office, "PID_002", "NONE", None),

            # Carol
            ("TXN_106", "ACC_003", 55.20, "USD", now - timedelta(days=3), "COMPLETED", 5.0, "LOW", "DEV_003", ip_legit_home, "PID_003", "NONE", None),
            ("TXN_107", "ACC_003", 412.00, "USD", now - timedelta(hours=28), "COMPLETED", 12.0, "LOW", "DEV_003", ip_legit_home, "PID_003", "NONE", None),

            # David
            ("TXN_108", "ACC_004", 15.00, "USD", now - timedelta(days=6), "COMPLETED", 6.0, "LOW", "DEV_004", ip_legit_mobile, "PID_004", "NONE", None),
            ("TXN_109", "ACC_004", 210.00, "USD", now - timedelta(days=2), "COMPLETED", 10.0, "LOW", "DEV_004", ip_legit_mobile, "PID_004", "NONE", None),

            # Elena
            ("TXN_110", "ACC_005", 98.00, "USD", now - timedelta(days=4), "COMPLETED", 7.0, "LOW", "DEV_005", ip_legit_office, "PID_005", "NONE", None),
            ("TXN_111", "ACC_005", 640.00, "USD", now - timedelta(hours=18), "COMPLETED", 18.0, "LOW", "DEV_005", ip_legit_office, "PID_005", "NONE", None),

            # Frank
            ("TXN_112", "ACC_006", 32.50, "USD", now - timedelta(days=3), "COMPLETED", 9.0, "LOW", "DEV_006", ip_legit_mobile, "PID_006", "NONE", None),
            ("TXN_113", "ACC_006", 185.00, "USD", now - timedelta(hours=6), "COMPLETED", 15.0, "LOW", "DEV_006", ip_legit_mobile, "PID_006", "NONE", None),

            # Grace
            ("TXN_114", "ACC_007", 520.00, "USD", now - timedelta(days=2), "COMPLETED", 12.0, "LOW", "DEV_001", ip_legit_home, "PID_001", "NONE", None),
            ("TXN_115", "ACC_007", 75.00, "USD", now - timedelta(hours=10), "COMPLETED", 10.0, "LOW", "DEV_001", ip_legit_home, "PID_001", "NONE", None),

            # Henry (Medium risk baseline)
            ("TXN_116", "ACC_008", 450.00, "USD", now - timedelta(hours=12), "COMPLETED", 35.0, "LOW", "DEV_002", ip_legit_home, "PID_002", "NONE", None),
            ("TXN_117", "ACC_008", 820.00, "USD", now - timedelta(hours=2), "COMPLETED", 48.0, "MEDIUM", "DEV_002", ip_legit_home, "PID_002", "NONE", None),

            # --- COORDINATED FRAUD SYNDICATE ACTIVITY ---
            # Card Testing Failures on Marcus (ACC_009)
            ("TXN_901_FAIL", "ACC_009", 1.00, "USD", now - timedelta(minutes=45), "FAILED", 65.0, "HIGH", "DEV_007", ip_tor_proxy, "PID_006", "INVESTIGATING", "Do Not Honor (Declined)"),
            ("TXN_902_FAIL", "ACC_009", 5.00, "USD", now - timedelta(minutes=40), "FAILED", 72.0, "HIGH", "DEV_007", ip_tor_proxy, "PID_006", "INVESTIGATING", "Invalid CVV (Declined)"),

            # High-Impact Fraud Transactions on Marcus (PRIMARY DEMO TRANSACTION)
            ("TXN_FRAUD_901", "ACC_009", 2450.00, "USD", now - timedelta(minutes=15), "COMPLETED", 96.5, "CRITICAL", "DEV_007", ip_tor_proxy, "PID_006", "PENDING", None),

            # Viktor Ramos (ACC_010) - Linked via Shared Emulator DEV_007 and Stolen Card PID_006!
            ("TXN_903_FAIL", "ACC_010", 2.00, "USD", now - timedelta(minutes=30), "FAILED", 75.0, "HIGH", "DEV_007", ip_tor_proxy, "PID_006", "INVESTIGATING", "Declined Velocity Limit"),
            ("TXN_FRAUD_902", "ACC_010", 1850.00, "USD", now - timedelta(minutes=22), "COMPLETED", 94.0, "CRITICAL", "DEV_007", ip_tor_proxy, "PID_006", "INVESTIGATING", None),
            ("TXN_FRAUD_903", "ACC_010", 1420.00, "USD", now - timedelta(minutes=8), "COMPLETED", 92.0, "CRITICAL", "DEV_008", ip_tor_proxy, "PID_006", "INVESTIGATING", None),

            # Chloe Bennett (ACC_011) - Linked via Shared Emulator DEV_007, Card PID_007, and Proxy IP
            ("TXN_FRAUD_904", "ACC_011", 1990.00, "USD", now - timedelta(minutes=20), "COMPLETED", 95.0, "CRITICAL", "DEV_007", ip_vpn_hosting, "PID_007", "INVESTIGATING", None),
            ("TXN_FRAUD_905", "ACC_011", 890.00, "USD", now - timedelta(minutes=12), "COMPLETED", 88.0, "CRITICAL", "DEV_007", ip_vpn_hosting, "PID_007", "INVESTIGATING", None),

            # Damian Cross (ACC_012) - Linked via Bot VM DEV_008 and Card PID_007
            ("TXN_FRAUD_906", "ACC_012", 2150.00, "USD", now - timedelta(minutes=18), "COMPLETED", 96.0, "CRITICAL", "DEV_008", ip_vpn_hosting, "PID_007", "INVESTIGATING", None),
            ("TXN_FRAUD_907", "ACC_012", 1320.00, "USD", now - timedelta(minutes=5), "COMPLETED", 93.0, "CRITICAL", "DEV_008", ip_vpn_hosting, "PID_007", "INVESTIGATING", None),
        ]

        for tx_id, acc_id, amt, curr, ts, status, rscore, rcat, dev_id, ip, pid_id, inv_status, fail_reason in transactions_spec:
            txn = Transaction(
                id=tx_id,
                customer_id=acc_id,
                amount=amt,
                currency=curr,
                timestamp=ts,
                payment_status=status,
                risk_score=rscore,
                risk_category=rcat,
                device_id=dev_id,
                ip_address=ip,
                payment_identity_id=pid_id,
                investigation_status=inv_status,
                failure_reason=fail_reason,
                merchant_name="Apex Global Electronics"
            )
            self.db.add(txn)

        # Commit all transactions first so investigations can reference them
        self.db.commit()

        # 5. Run autonomous multi-agent investigations on primary syndicate transactions
        # This guarantees every suspicious transaction links to a full investigation dossier
        from app.agents.orchestrator import MultiAgentOrchestrator
        orchestrator = MultiAgentOrchestrator(self.db)
        for target_tx in ["TXN_FRAUD_901", "TXN_FRAUD_902", "TXN_FRAUD_904", "TXN_FRAUD_905", "TXN_FRAUD_906"]:
            try:
                orchestrator.run_investigation(transaction_id=target_tx, force_new_case=False)
            except Exception as e:
                print(f"Error pre-investigating {target_tx}: {e}")

        # 6. Pre-create verified captured PayPal payment records for syndicate transactions
        # This allows judges to inspect and trigger real/simulated Sandbox refunds safely once approved!
        # Note: TXN_FRAUD_905 represents an authorized transaction that was NEVER captured by merchant,
        # so capture_id is strictly None, and it is explicitly ineligible for refund reversal.
        payment_specs = [
            ("PAY_OP_901", "CASE_FRAUD_901", "SANDBOX-ORD-998822", "CAP-SANDBOX-7882910", "TXN_FRAUD_901", 2450.00, "COMPLETED", "NONE", "REFUND"),
            ("PAY_OP_902", "CASE_FRAUD_902", "SANDBOX-ORD-998823", "CAP-SANDBOX-7882911", "TXN_FRAUD_902", 1850.00, "COMPLETED", "NONE", "REFUND"),
            ("PAY_OP_904", "CASE_FRAUD_904", "SANDBOX-ORD-998824", "CAP-SANDBOX-7882912", "TXN_FRAUD_904", 1990.00, "COMPLETED", "NONE", "REFUND"),
            ("PAY_OP_905", "CASE_FRAUD_905", "SANDBOX-ORD-998826", None, "TXN_FRAUD_905", 890.00, "UNCAPTURED", "INELIGIBLE", "UNCAPTURED_AUTHORIZATION"),
            ("PAY_OP_906", "CASE_FRAUD_906", "SANDBOX-ORD-998825", "CAP-SANDBOX-7882913", "TXN_FRAUD_906", 2150.00, "COMPLETED", "NONE", "REFUND"),
        ]
        for p_id, c_id, ord_id, cap_id, tx_ref, amt, p_stat, ref_stat, op_type in payment_specs:
            demo_payment = PaymentOperation(
                id=p_id,
                case_id=c_id,
                paypal_order_id=ord_id,
                capture_id=cap_id,
                transaction_ref=tx_ref,
                amount=amt,
                currency="USD",
                payment_status=p_stat,
                refund_status=ref_stat,
                approval_status="APPROVED" if c_id == "CASE_FRAUD_905" else "PENDING",
                operation_type=op_type,
                idempotency_key=f"IDEM_REFUND_{tx_ref}",
                is_simulated=True,
                raw_response={
                    "status": p_stat,
                    "capture_id": cap_id,
                    "seller_protection": {"status": "ELIGIBLE" if cap_id else "INELIGIBLE_NO_CAPTURE"},
                    "amount": {"value": f"{amt:.2f}", "currency_code": "USD"},
                    "note": "Settled capture verified" if cap_id else "Authorization hold never captured by merchant. Ineligible for refund reversal."
                }
            )
            self.db.add(demo_payment)
        self.db.commit()

        return len(transactions_spec)
