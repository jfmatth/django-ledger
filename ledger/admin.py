from django.contrib import admin

# Register your models here.

from ledger.models import RawCSV, RawTransaction, Ledger

class RawCSVAdmin(admin.ModelAdmin):
    pass
admin.site.register(RawCSV, RawCSVAdmin)


class RawTransactionAdmin(admin.ModelAdmin):
    list_display = ["transactionDate", "symbol", "action", "quantity", "totalAmount", "ledgerEntry"]
    list_filter = ['ingested', 'action',"strikeSymbol"]
admin.site.register(RawTransaction, RawTransactionAdmin)


class TransactionInLine(admin.TabularInline):
    model = RawTransaction
    extra = 0


class LedgerAdmin(admin.ModelAdmin):
    list_display = ["symbol", "status", "opened", "investedAmount", "closedAmount", "perc_profit" ]
    list_filter = ['status']

    inlines = [
        TransactionInLine,
    ]



admin.site.register(Ledger, LedgerAdmin)
