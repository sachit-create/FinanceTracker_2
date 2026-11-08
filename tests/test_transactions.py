import unittest

from flaskApp.app import app, db
from flaskApp.models import Transaction, User


class TransactionFlowTests(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SECRET_KEY="test-secret",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        )
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()

            user = User(username="alice")
            user.set_password("secret")
            db.session.add(user)
            db.session.commit()
            self.user = user

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_add_list_and_delete_transaction_for_logged_in_user(self):
        login_response = self.client.post(
            "/login",
            data={"username": "alice", "password": "secret"},
            follow_redirects=True,
        )
        self.assertEqual(login_response.status_code, 200)

        create_response = self.client.post(
            "/addtrac",
            data={
                "amount": "125.50",
                "type": "debit",
                "description": "Groceries",
            },
            follow_redirects=True,
        )
        self.assertEqual(create_response.status_code, 200)

        with app.app_context():
            txn = Transaction.query.filter_by(uid=self.user.uid).first()
            self.assertIsNotNone(txn)
            self.assertEqual(str(txn.amount), "125.50")
            self.assertEqual(txn.type, "debit")
            self.assertEqual(txn.description, "Groceries")

        list_response = self.client.get("/transactions")
        self.assertEqual(list_response.status_code, 200)
        self.assertIn(b"Groceries", list_response.data)

        delete_response = self.client.post(
            f"/transactions/delete/{txn.tid}",
            follow_redirects=True,
        )
        self.assertEqual(delete_response.status_code, 200)

        with app.app_context():
            deleted_txn = Transaction.query.filter_by(tid=txn.tid).first()
            self.assertIsNone(deleted_txn)


if __name__ == "__main__":
    unittest.main()
