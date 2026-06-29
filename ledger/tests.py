import csv
import tempfile
import os

from django.test import TestCase

import ledger.command_loader as loader

from ledger.models import RawCSV, RawTransaction, Ledger

import logging
logger = logging.getLogger(__name__)

FILE_SIMPLECSP = 'tests/simple-csp.csv'
FILE_SIMPLECSPREV = 'tests/simple-csp-reversed.csv'
FILE_SIMPLEASSIGN = 'tests/simple-assignment.csv'

class loaderTest(TestCase):
    def setUp(self):
        loader.loadCSV(FILE_SIMPLECSP)

    def test_1_csvrecord(self):
        # once loaded, we should have one record in the RawCSV table
        self.assertEqual(RawCSV.objects.all().count(), 1)

    def test_1a_fields(self):
        # check all the fields are loaded too
        self.assertEqual(RawCSV.objects.get(pk=1).filename, FILE_SIMPLECSP) 
        self.assertEqual(RawCSV.objects.get(pk=1).ingested, False)

    def test_2_buildTransactions(self):
        loader.buildTransactions()

        # All transactions are built, so see if there are two transactions
        self.assertEqual(RawTransaction.objects.all().count(),2)

# These are full body tests, for each option case scenario
class simpleCSP(TestCase):
    def setUp(self):
        loader.loadCSV(FILE_SIMPLECSP)
        loader.buildTransactions()
        loader.buildStrikeInfo()
        loader.updateLedger()
        
    def test_1(self):
        # Verify that a simple
        rec = Ledger.objects.get(pk=1)

        self.assertEqual(Ledger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)

class simpleCSPReversed(TestCase):
    def setUp(self):
        loader.loadCSV(FILE_SIMPLECSPREV)
        loader.buildTransactions()
        loader.buildStrikeInfo()
        loader.updateLedger()
        
    def test_1(self):
        # Verify that a simple
        rec = Ledger.objects.get(pk=1)

        self.assertEqual(Ledger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)

class simpleAssignment(TestCase):
    def setUp(self):
        loader.loadCSV(FILE_SIMPLEASSIGN)
        loader.buildTransactions()
        loader.buildStrikeInfo()
        loader.updateLedger()
        
    def test_1(self):
        # Verify that a simple
        rec = Ledger.objects.get(pk=1)

        self.assertEqual(Ledger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)

# rows = [
#     ['Date', 'Action', 'Symbol', 'Description', 'Quantity', 'Price', 'Fees & Comm', 'Amount'],
#     ['07/25/2025', 'Sell to Open', 'T 08/22/2025 29.00 C', 'CALL AT&T INC $29 EXP 08/22/25', '15', '$0.34', '$9.95', '$500.05'],
#     ['07/25/2025', 'Buy to Open', 'LCID 09/19/2025 2.50 P', 'PUT LUCID GROUP INC $2.5 EXP 09/19/25', '10', '$0.21', '$6.61', '-$216.61']
# ]

# flatten_rows = lambda lst: '\n'.join([','.join(row) for row in lst])
# TRANSACTION_COUNT = 2

# def loadRows():
#     # Creates a RawCSV record to read from
#     record = RawCSV()
#     record.filename = "test"
#     record.data = flatten_rows(rows)
#     record.ingested = False
#     record.save()


# class loadCSVTestCase(TestCase):
#     """
#         Since we don't read in a file, we fake it here with loadRows()
#     """
#     def setUp(self):
#         loadRows()

#     def test_1_csv_load(self):
#         r = RawCSV.objects.all()[0]

#         self.assertEqual(r.filename, "test")
#         self.assertEqual(r.ingested, False)
#         self.assertEqual(len(RawCSV.objects.all()), 1)

#     def tearDown(self):
#         pass


# class buildTransactionTestCase(TestCase):

#     def setUp(self):
#         loadRows()
#         buildTransactions()
        
#     def test_1_buildTransaction(self):
#         ## We load the CSV and Build the RawTransaction objects
#         self.assertEqual(len(RawTransaction.objects.all() ), TRANSACTION_COUNT)