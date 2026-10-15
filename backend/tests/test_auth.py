import unittest

from app.services.auth import DuplicateStudentIDError, InMemoryAuthStore


class InMemoryAuthStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryAuthStore()

    def test_register_and_login_issue_distinct_tokens(self) -> None:
        registered = self.store.register("student-1", "secure-password")
        logged_in = self.store.login("student-1", "secure-password")

        self.assertIsNotNone(logged_in)
        self.assertEqual(registered.student_id, logged_in.student_id)
        self.assertNotEqual(registered.access_token, logged_in.access_token)

    def test_login_rejects_unknown_student_or_wrong_password(self) -> None:
        self.store.register("student-1", "secure-password")

        self.assertIsNone(self.store.login("missing", "secure-password"))
        self.assertIsNone(self.store.login("student-1", "wrong-password"))

    def test_register_rejects_duplicate_student_id(self) -> None:
        self.store.register("student-1", "secure-password")

        with self.assertRaises(DuplicateStudentIDError):
            self.store.register("student-1", "another-password")

    def test_token_lookup_returns_student_id_only_for_issued_tokens(self) -> None:
        session = self.store.register("student-1", "secure-password")

        self.assertEqual(
            self.store.get_student_id_for_token(session.access_token),
            "student-1",
        )
        self.assertIsNone(self.store.get_student_id_for_token("unknown-token"))


if __name__ == "__main__":
    unittest.main()