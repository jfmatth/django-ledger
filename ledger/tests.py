import csv
import tempfile
import os

from django.test import TestCase

import ledger.command_loader as loader
from ledger.models import RawCSV, RawTransaction, OptionLedger

import logging
logger = logging.getLogger(__name__)

FILE_SIMPLECSP = 'tests/simple-csp.csv'
FILE_SIMPLECSPREV = 'tests/simple-csp-reversed.csv'
FILE_SIMPLEASSIGN = 'tests/simple-assignment.csv'
FILE_SIMPLEEXPIRE = 'tests/simple-expire.csv'
FILE_PARTIALCSP = 'tests/partial-csp.csv'

FILE_SIMPLEBUY = "tests/simple-buy.csv"

class loaderTest(TestCase):
    # Test that the loader and buildstransactions actually do what we need 

    def setUp(self):
        loader.loadCSV(FILE_SIMPLECSP)

    def test_100_csvrecord(self):
        # once loaded, we should have one record in the RawCSV table
        self.assertEqual(RawCSV.objects.all().count(), 1)

    def test_20_fields(self):
        # check all the fields are loaded too
        self.assertEqual(RawCSV.objects.get(pk=1).filename, FILE_SIMPLECSP) 
        self.assertEqual(RawCSV.objects.get(pk=1).ingested, False)

    def test_30_buildTransactions(self):
        loader.buildTransactions()

        # All transactions are built, so see if there are two transactions
        self.assertEqual(RawTransaction.objects.all().count(),2)


class loaderDuplicateTest(TestCase):
    # verify that loading the same CSV will NOT duplicate RawTransactions

    def setUp(self):
        loader.loadCSV(FILE_SIMPLECSP)
        loader.loadCSV(FILE_SIMPLECSP)

    def test_10_csvrecord(self):
        # once loaded, we should have one record in the RawCSV table
        self.assertEqual(RawCSV.objects.all().count(), 2)

    def test_20_fields(self):
        # check all the fields are loaded too
        self.assertEqual(RawCSV.objects.get(pk=1).filename, FILE_SIMPLECSP) 
        self.assertEqual(RawCSV.objects.get(pk=1).ingested, False)
        self.assertEqual(RawCSV.objects.get(pk=2).filename, FILE_SIMPLECSP) 
        self.assertEqual(RawCSV.objects.get(pk=2).ingested, False)

    def test_30_buildTransactions(self):
        loader.buildTransactions()

        # All transactions are built, so see if there are two transactions
        self.assertEqual(RawTransaction.objects.all().count(),2)


class simpleCSP(TestCase):
    # Load a simple CSP transaction set (STO -> BTC), should close it out and show the profit

    def setUp(self):
        loader.load(FILE_SIMPLECSP)
        
    def test_10_csp_sucess(self):
        # Verify that a simple
        rec = OptionLedger.objects.get(pk=1)

        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)


class partialCSP(TestCase):
    # See what happens when we only sell part of a CSP

    def setUp(self):
        loader.load(FILE_PARTIALCSP)
        
    def test_10_csp_partial_sucess(self):
        # Not closed, and qty > 0
        rec = OptionLedger.objects.get(pk=1)

        # it should still be open
        self.assertEqual(rec.status, "Open")
        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertGreater(rec.quantity, 0)



class simpleCSPReversed(TestCase):
    # Same as simpleCSP, but the transactions are loaded in reverse, just to make sure it doesn't matter

    def setUp(self):
        loader.load(FILE_SIMPLECSP)
        # loader.loadCSV(FILE_SIMPLECSPREV)
        # loader.buildTransactions()
        # loader.buildStrikeInfo()
        # loader.updateLedger()
        
    def test_10_csp_sucess(self):
        # Verify that a simple
        rec = OptionLedger.objects.get(pk=1)

        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)



class simpleAssignment(TestCase):
    # STO -> Assigned

    def setUp(self):
        loader.load(FILE_SIMPLEASSIGN)
        
    def test_10_csp_assign_sucess(self):
        # Verify that a simple
        rec = OptionLedger.objects.get(pk=1)

        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)


class simpleCSPReversed(TestCase):
    # Same as simpleCSP, but the transactions are loaded in reverse, just to make sure it doesn't matter

    def setUp(self):
        loader.loadCSV(FILE_SIMPLECSPREV)
        loader.buildTransactions()
        loader.buildStrikeInfo()
        loader.updateLedgers()
        
    def test_1(self):
        # Verify that a simple
        rec = OptionLedger.objects.get(pk=1)

        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)



class simpleAssignment(TestCase):
    # Test STO -> Assigned

    def setUp(self):
        loader.loadCSV(FILE_SIMPLEASSIGN)
        loader.buildTransactions()
        loader.buildStrikeInfo()
        loader.updateLedgers()
        
    def test_1(self):
        # Verify that a simple
        rec = OptionLedger.objects.get(pk=1)

        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)


class simpleExpire(TestCase):
    # Test STO -> Expire

    def setUp(self):
        loader.load(FILE_SIMPLEEXPIRE)
        
    def test_10_csp_expire(self):
        # There should be one record in the Ledger
        rec = OptionLedger.objects.get(pk=1)

        self.assertEqual(OptionLedger.objects.all().count(), 1)
        self.assertEqual(rec.status, "Closed")
        self.assertEqual(rec.quantity, 0)


class simpleBuy(TestCase):

    def setUp(self):
        loader.load(FILE_SIMPLEBUY)

