from django.core.management.base import BaseCommand
import logging

from ...command_loader import loadCSV, buildStrikeInfo, buldTransactions, updateLedger

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "Filename"
    help = "Loads transactions from CSV"

    logger.info("Command")

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="+")

    def handle(self, *args, **options):
        loadCSV(options['filename'][0])
        buldTransactions()
        buildStrikeInfo()
        updateLedger()
