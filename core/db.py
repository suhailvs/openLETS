"""
Database Acess Layer
"""

import datetime
import itertools
import operator

from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from core import models


def get_balance(usera, userb, currency):
    """Load a balance between two users."""
    return (
        models.UserBalance.objects.select_related("balance")
        .get(user=usera, balance__users=userb, balance__currency=currency)
        .balance
    )


def get_balances(user, include_balanced=False, credited=None):
    """Get the list of balances for a user. Filter out any where the value is
    back to 0.
    """
    q = models.UserBalance.objects.filter(user=user)
    if not include_balanced:
        q = q.exclude(balance__value=0)
    if credited is not None:
        q = q.filter(credited=credited)
    return q


def get_balances_many(users, currency, credited, include_balanced=False):
    """Return a map of user -> balances."""
    q = models.UserBalance.objects.filter(
        user__in=users, credited=credited, balance__currency=currency
    )
    if not include_balanced:
        q = q.exclude(balance__value=0)
    return q


def get_pending_trans_for_user(user):
    """Get pending transactions for a user which were
    created by some other user, and need to be accepted.
    """
    return models.TransactionRecord.objects.filter(
        target_user=user, transaction__isnull=True, rejected=False
    )


def get_recent_trans_for_user(user, days=10, limit=15, pending_only=False):
    """Get recent transaction records for the user.  These transaction records
    may be confirmed.
    """
    earliest_day = datetime.date.today() - datetime.timedelta(days)
    q = models.TransactionRecord.objects.filter(
        creator_user=user, time_created__gte=earliest_day
    )

    if pending_only:
        q = q.filter(transaction__isnull=True)

    return q.order_by("-transaction_time")[:limit]


def get_exchange_rates(user):
    """Get exchange rates for the user."""
    return models.ExchangeRate.objects.filter(user=user)


# TODO: tests
def get_transfer_history(user, filters):
    """Get a list of all transactions and resolutions for the user filtered
    by form filters.
    """
    query_sets = []
    resolution_query, trans_query = [], []
    now = datetime.datetime.now()

    def conv(key, trans, resolution, coerce_val=None):
        """Helper to setup filters for both tables."""
        val = filters.get(key)
        if not val:
            return
        if coerce_val:
            val = coerce_val(val)
        if trans:
            trans_query.append((trans, val))
        if resolution:
            resolution_query.append((resolution, val))

    # Setup filters
    transfer_type = filters.get("transfer_type")
    conv("user", "target_user", "resolution__users")
    conv("transaction_type", "from_receiver", "credited", lambda x: x == "charge")
    conv("currency", "currency", "resolution__currency")

    if filters.get("status") == "rejected":
        conv("status", "rejected", None, lambda x: True)
    else:
        conv(
            "status",
            "transaction__time_confirmed__isnull",
            "resolution__time_confirmed__isnull",
            lambda x: x == "pending",
        )

    conv(
        "transaction_time",
        "transaction_time__gt",
        "resolution__time_confirmed__gt",
        lambda d: now - datetime.timedelta(days=d),
    )

    conv(
        "confirmed_time",
        "transaction__time_confirmed__gt",
        "resolution__time_confirmed__gt",
        lambda d: now - datetime.timedelta(days=d),
    )

    # Query Transactions
    if not transfer_type or transfer_type == "transaction":
        query_sets.append(
            models.TransactionRecord.objects.filter(
                creator_user=user, **dict(trans_query)
            )
        )

    # Query Resolutions
    if not transfer_type or transfer_type == "resolution":
        query_sets.append(
            models.UserResolution.objects.filter(
                user=user, **dict(resolution_query)
            )
        )

    # Merge results
    return sorted(
        itertools.chain.from_iterable(query_sets),
        key=operator.attrgetter("transaction_time"),
        reverse=True,
    )


def get_trans_record_for_user(trans_record_id, user):
    """Get a transaction record for a user."""
    return models.TransactionRecord.objects.get(
        id=trans_record_id, target_user=user, rejected=False
    )


@transaction.atomic
def reject_trans_record(trans_record_id, user):
    """Reject a transaction record where the user is the target."""
    trans_record = get_trans_record_for_user(trans_record_id, user)
    trans_record.rejected = True
    trans_record.save()


@transaction.atomic
def confirm_trans_record(trans_record):
    """Confirm a transaction record."""
    # Build and save matching record
    confirm_record = models.TransactionRecord(
        creator_user=trans_record.target_user,
        target_user=trans_record.creator_user,
        from_receiver=not trans_record.from_receiver,
        currency=trans_record.currency,
        transaction_time=trans_record.transaction_time,
        value=trans_record.value,
    )
    transaction = models.Transaction()
    transaction.save()

    confirm_record.transaction_id = trans_record.transaction_id = transaction.id
    confirm_record.save()
    trans_record.save()

    # Update the balance, or create a new one
    update_balance(trans_record, trans_record.provider, trans_record.receiver)


# TODO: tests!
def update_balance(currency_type, provider, receiver):
    """Update or create a balance between two users for a currency. Should be
    called from a method that was already created a transfer.
    """
    try:
        balance = get_balance(provider, receiver, currency=currency_type.currency)
    except ObjectDoesNotExist:
        return new_balance(currency_type, provider, receiver)

    # Establish the direction of the transfer
    if provider == balance.debted:
        balance.value += currency_type.value
        balance.save()
        return balance

    balance.value -= currency_type.value
    if (balance.value) < 0:
        balance.value = abs(balance.value)
        for userbalance in balance.userbalance_set.all():
            userbalance.credited = not userbalance.credited
            userbalance.save()

    balance.save()
    # TODO: does this cascade to the userbalance ?
    return balance


# TODO: tests
def new_balance(currency_type, provider, receiver):
    balance = models.Balance(currency=currency_type.currency, value=currency_type.value)
    balance.save()
    userbalancea = models.UserBalance(
        user=provider, credited=False, balance=balance
    )
    userbalanceb = models.UserBalance(
        user=receiver, credited=True, balance=balance
    )
    userbalancea.save()
    userbalanceb.save()
    balance.save()
    return balance


def get_transaction_count(user):
    """Get a count of transaction records by this user."""
    return models.TransactionRecord.objects.filter(creator_user=user).count()


def get_transaction_notifications(user, days=2):
    """Get recent transaction actions targetted at the user."""
    now = datetime.datetime.now()
    return models.TransactionRecord.objects.filter(
        target_user=user, time_created__gte=now - datetime.timedelta(days=days)
    )


def get_recent_resolutions(user, days=2):
    """Get recent resolutions involsing the user."""
    now = datetime.datetime.now()
    return models.UserResolution.objects.filter(
        user=user,
        resolution__time_confirmed__gte=now - datetime.timedelta(days=days),
    )
