import csv, hashlib, datetime
from decimal import Decimal
from io import StringIO
from decimal import Decimal
from enum import StrEnum
import re

import logging

from django.core.exceptions import ObjectDoesNotExist

from ledger.models import RawCSV, RawTransaction, Ledger

logger = logging.getLogger(__name__)

class Action(StrEnum):
    BTC = "Buy to Close"
    STO = "Sell to Open"
    ASSIGNED = "Assigned"
    EXPIRED = "Expired"

def dollars_to_decimal(s: str) -> Decimal:
    s = s.strip()
    s = s.replace("(", "-").replace(")", "")  # accounting negatives
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    return Decimal(cleaned)

def schwab_date(datestr):
    # converts an incoming transaction date to the right date
    # some transactions have a "<date1> as of <date2>" entry for some stupid reason, when the date of the transaction
    # is date2, lame

    d = None
    if "as of" in datestr:
        # return the last 10 digits from the string
        d = datestr[-10:]
    else:
        d = datestr[:10]

    return datetime.datetime.strptime(d,"%m/%d/%Y")

def hash_transaction(transaction):
    """Generate a unique SHA-256 hash for a gi8ven transaction."""
    # transaction_string = ",".join(transaction)  # Convert transaction to a string

    return hashlib.sha256(transaction.encode()).hexdigest()


def loadCSV(filename):

    logger.info(f"Loading {filename}..")

    with open(filename,"r") as f:
        temp = RawCSV()
        temp.filename = filename
        temp.data = f.read()
        temp.ingested = False
        temp.save()

    logger.info(f"Loaded")


def buildTransactions():
    """
    Converts from CSV into records in our Table
    """

    for csvtransaction in RawCSV.objects.filter(ingested=False):

        logger.info(f'building Transactions from CSV {csvtransaction}')

        with StringIO(csvtransaction.data) as csvfile:
            reader = csv.DictReader(csvfile)
    
            for transaction in reader:
                # see if we have to add this record, or if it's already there based on the hashid
                hash = hash_transaction("".join(transaction.values() ) )
                try:
                    RawTransaction.objects.get(hashID=hash)
                    logger.debug(f"duplicate {transaction}")
                except ObjectDoesNotExist:

                    logging.debug(f"Adding {transaction}")
                    
                    record = RawTransaction()

                    record.transactionDate  = schwab_date(transaction['Date'].strip())
                    record.action           = transaction['Action'].strip()
                    record.symbol           = transaction['Symbol'].strip()
                    record.description      = transaction['Description'].strip()
                    record.quantity         = float(dollars_to_decimal(transaction['Quantity']))  if transaction['Quantity'] != "" else 0
                    record.price            = float(dollars_to_decimal(transaction['Price'])) if transaction['Price'] != "" else 0
                    record.extrafees        = 0
                    record.totalAmount      = float(dollars_to_decimal(transaction['Amount']) ) if transaction['Amount'] != "" else 0

                    record.hashID           = hash

                    logger.debug(f"Saving transaction {record}")
                    record.save()

        csvtransaction.ingested = True
        csvtransaction.processed = False
        csvtransaction.save()


def buildStrikeInfo():
    """
    Goes through all the transactions and builds the strike information for options, everything that isn't already processed.
    """

    logger.info(f"Building StrikeInfo")

    for transaction in RawTransaction.objects.filter(processed = False):
        logger.debug("Building Strike Info")

        if transaction.action in Action._value2member_map_:
            logger.debug(f"Processing {transaction}")

            parts = transaction.symbol.split(" ") # Break out the parts of the symbol for an option action [symbol,date, price, P or C]
            logger.debug(f"Parts: {parts}")

            # Parts: ['IWM', '06/12/2025', '210.00', 'P']
            transaction.strikeSymbol    = parts[0]
            transaction.strikeDate      = datetime.datetime.strptime(parts[1],"%m/%d/%Y")
            transaction.strikePrice     = parts[2]
            transaction.strikeSide      = parts[3]

            transaction.processed = True

        # # Determine which other reords we can mark as processed?
        # if transaction.action in NON_ACTIONS:
        #     transaction.processed = True

        transaction.save()


def updateLedger():
    """
    Creates or updates ledgers on anything that's not processed

    This is the meat of the program for now, make ledgers for tracking how we did on option sales
    """

    logger.info("Updating Ledger...")

    for transaction in RawTransaction.objects.filter(ingested=False).order_by("transactionDate"):
        logger.debug(f"matching {transaction}")
        
        # are any options actions in what's in transaction.action?
        if transaction.action in Action._value2member_map_:

            l, created = Ledger.objects.get_or_create(symbol=transaction.symbol, status="Open")

            logger.debug(f"{transaction.action}")

            match transaction.action:
                case Action.STO:
                    # We've sold an option, might be the first one for this "symbol" or adding to it
                    if created:
                        # we created a new STO CSP (probably) so set the dtes and amounts
                        l.opened = transaction.transactionDate
                        l.investedAmount = transaction.totalAmount
                        l.status = "Open"

                    # This might be added to an existing record, in which case we add to it, or if it's new, its starting at 0
                    l.closedAmount += transaction.totalAmount
                    l.quantity += transaction.quantity

                case Action.BTC | Action.ASSIGNED | Action.EXPIRED :
                    # Option is done, most likely, so close it out.
                    logger.debug(f'{transaction}\n, {l}')

                    # if created:
                    #     l.opened = transaction.transactionDate
                    #     l.status = "Open"

                    l.closed = transaction.transactionDate
                    if transaction.action == Action.ASSIGNED or transaction.action == Action.EXPIRED:
                        l.closedAmount = 0
                        l.status = "Closed"
                        # should we checkt that the amount of the closing amount matches what's open?  FOR NOW - no.
                        l.quantity = 0
                    else:
                        l.closedAmount += transaction.totalAmount
                        l.quantity -= transaction.quantity

            # if we have balanced out our qty, most likely we are done, so close this ledger
            if l.quantity == 0:
                l.status = "Closed"

            l.save()

            #  attach this leedger entry to the transaction, for the 1:N relation
            transaction.ledgerEntry = l
            transaction.ingested = True
            transaction.save()

            logger.debug(f"Processes transaction {transaction}")

def load(filename):
    loadCSV(filename)
    process()

def process():
    # run all processing without the loading :)
    buildTransactions()
    buildStrikeInfo()
    updateLedger()
