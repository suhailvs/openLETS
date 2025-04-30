from django.db import models as m
from django.contrib.auth.models import User
from decimal import Decimal
import itertools
# Create your models here.
class Person(m.Model):
    """A person. This model is the auth profile model."""

    user = m.OneToOneField(User, on_delete=m.CASCADE)
    default_currency =  m.ForeignKey("Currency", on_delete=m.CASCADE, null=True)

    def __str__(self):
        return self.user.username

    def transaction_records(self):
        return itertools.chain(
            self.transaction_records_creator, self.transaction_records_target
        )
