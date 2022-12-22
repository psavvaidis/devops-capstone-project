"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
    
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        talisman.force_https = False
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_get_accounts(self):
        """It should return all accounts"""
        response = self.client.get(BASE_URL)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        accounts = self._create_accounts(5)
        response = self.client.get(BASE_URL)
        existing_accounts = response.get_json()
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(len(existing_accounts), len(accounts))
        for index in range(len(accounts)):
            self.assertEqual(existing_accounts[index]["id"], accounts[index].id)

    def test_read_an_account(self):
        """It should return an account given its id"""
        response = self.client.get('{url}/{id}'.format(url=BASE_URL, id=0))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        accounts = self._create_accounts(1)
        response = self.client.get('{url}/{id}'.format(url=BASE_URL, id=accounts[0].id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found_account = response.get_json()
        self.assertEqual(found_account, accounts[0].serialize())

    def test_update_account(self):
        """It should return an account updated given its id and new data"""
        response = self.client.put('{url}/{id}'.format(url=BASE_URL, id=0))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        account = self._create_accounts(1)
        new_account = AccountFactory()
        response = self.client.put('{url}/{id}'.format(url=BASE_URL, id=account[0].id), json=new_account.serialize())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_account = response.get_json()
        self.assertEqual(updated_account["id"],account[0].id)
        self.assertEqual(updated_account["name"],new_account.name)
        self.assertEqual(updated_account["email"],new_account.email)
        self.assertEqual(updated_account["address"],new_account.address)
        self.assertEqual(updated_account["phone_number"],new_account.phone_number)
        self.assertEqual(updated_account["date_joined"], str(new_account.date_joined))

    def test_delete_account(self):
        """It should delete an existing account given its id"""
        account = self._create_accounts(1)
        response = self.client.delete('{url}/{id}'.format(url=BASE_URL, id=account[0].id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_method_not_allowed(self):
        """It should not allow an illegal method call"""
        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_secure_headers(self):
        """It should find secure headers"""
        result = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        expected = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        for key, value in expected.items():
            self.assertEqual(result.headers.get(key), value)