from django.core.management.base import BaseCommand
import logging

import ledger.command_loader as loader

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "Filename"
    help = "Loads transactions from CSV"

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="+")

    def handle(self, *args, **options):
        # loader.loadCSV(options['filename'][0])
        # loader.buildTransactions()
        # loader.buildStrikeInfo()
        # loader.updateLedger()

        loader.load(options['filename'][0])