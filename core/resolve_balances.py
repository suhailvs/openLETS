"""
 Resolve balances between users.
"""

from collections import defaultdict
import logging

from django.db import transaction

from optparse import OptionParser
from core import models, db


class BalanceResolver(object):

    def setup_options(self):
        self.option_parser = parser = OptionParser()
        parser.add_option(
            "-l",
            "--chain-limit",
            dest="chain_limit",
            help="Limit the number of users in a resolution chain.",
            default=5,
        )
        parser.add_option("-v", "--verbose", dest="verbose", action="store_true")

    def load_options(self):
        self.options, self.args = self.option_parser.parse_args()

    def setup_logging(self):
        self.log = logging.getLogger("BalanceResolver")
        level = logging.DEBUG if self.options.verbose else logging.INFO
        self.log.setLevel(level)
        self.log.addHandler(logging.StreamHandler())
        self.stats = defaultdict(int)

    def get_balance_chain(self, users, target_balance, depth=0):
        """Find a balance from users with target_user which is credited
        according to `credited`. If a balance is not found recursively calls
        itself with all of the users for the last set of balances.
        """
        if depth > self.options.chain_limit:
            self.log.debug("Giving up at depth %s" % depth)
            self.stats["max_depth"] += 1
            return None
        if not users:
            return None

        credited = target_balance.credited
        target_user = target_balance.user
        currency = target_balance.balance.currency

        mirrored_balances = db.get_balances_many(users, currency, credited)
        self.log.debug(
            "  Found %s mirrored balances (%s)"
            % (len(mirrored_balances), set(pb.other_user for pb in mirrored_balances))
        )
        # TODO: chose the highest value balance
        for mirrored_balance in mirrored_balances:
            if target_user.id == mirrored_balance.other_user.id:
                return [mirrored_balance]

        mirrored_users = set(pb.other_user for pb in mirrored_balances)
        balance_chain = self.get_balance_chain(
            mirrored_users, target_balance, depth + 1
        )
        if not balance_chain:
            return

        # Find the balance in this context which links back to the original
        # balance
        link_user = balance_chain[-1].user
        for mirrored_balance in mirrored_balances:
            if mirrored_balance.other_user.id == link_user.id:
                balance_chain.append(mirrored_balance)
                return balance_chain

    def resolve_balances(self, balances):
        for balance in balances:
            self.log.debug(" Attempting to resolving balance %s" % balance)
            balance_chain = self.get_balance_chain([balance.other_user], balance)
            if balance_chain:
                self.resolve(balance_chain)

    @transaction.atomic
    def resolve(self, balance_chain):
        self.log.info(
            "Resolving %s with a chain of %s" % (balance_chain[-1], len(balance_chain))
        )
        self.stats["resolved"] += 1

        value = min(pb.balance.value for pb in balance_chain)
        for balance in balance_chain:
            objs = self.build_resolution(balance, value)
            self.save_resolution(*objs)

    def build_resolution(self, balance, value):
        currency = balance.balance.currency
        resolution = models.Resolution(value=value, currency=currency)
        pr_a = models.UserResolution(
            resolution=resolution, user=balance.user, credited=not balance.credited
        )
        pr_b = models.UserResolution(
            resolution=resolution,
            user=balance.other_user,
            credited=balance.credited,
        )
        return resolution, pr_a, pr_b

    def save_resolution(self, resolution, pr_a, pr_b):
        resolution.save()
        pr_a.resolution_id = pr_b.resolution_id = resolution.id
        pr_a.save()
        pr_b.save()

        # user b should be the provider
        db.update_balance(resolution, pr_b.user, pr_a.user)

    def run(self):
        """Run over all users and find chains of balances which will resolve
        down to lower balances.
        """
        users = models.User.objects.filter(is_active=True).all()
        for user in users:
            self.log.debug("Resolving balances for %s" % user)
            balances = db.get_balances(user, credited=False)
            self.resolve_balances(balances)

    def print_stats(self):
        self.log.info("\n".join("%-20s %s" % (k, v) for k, v in self.stats.items()))

    def start(self):
        self.setup_options()
        self.load_options()
        self.setup_logging()
        self.run()
        self.print_stats()


BalanceResolver().start()
