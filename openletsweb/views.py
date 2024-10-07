import datetime
import itertools
import json
from operator import itemgetter

from django.shortcuts import redirect
from django.views.decorators.http import require_POST, require_GET
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.contrib import messages
from django.conf import settings as config
from django.http import HttpResponse

from core import db
from openletsweb import forms
from openletsweb import web
from openletsweb import models
from openletsweb.util import trans_matcher


def index(request):
    if request.user.is_authenticated:
        return redirect("home")

    intro = models.Content.objects.get(name="intro", site=config.SITE_ID)
    context = {
        "login_form": forms.LoginForm(),
        "user_form": forms.UserCreateForm(web.form_data(request)),
        "intro": intro,
        "site": Site.objects.get(id=config.SITE_ID),
    }
    return web.render_context(request, "index.html", context=context)


def build_pending_trans_records(request):
    """Supplement the pending trans records with a modify form
    and attempt to link them to any trans_records created by the
    user.
    """
    recent_pending = db.get_recent_trans_for_user(
        request.user, limit=100, pending_only=True
    )
    pending_trans_records = db.get_pending_trans_for_user(request.user)
    for trans_record in pending_trans_records:
        cur_user_trans_record = None
        if trans_record.transaction:
            cur_user_trans_record = trans_record.other_trans_record

        trans_record.modify_form = forms.TransactionRecordForm(
            initial={
                "transaction_time": trans_record.transaction_time,
                "currency": trans_record.currency.id,
                "target_person": trans_record.creator_person.id,
                "value": trans_record.value_str,
                "from_receiver": trans_record.targets_transaction_type,
            },
            instance=cur_user_trans_record,
        )
        trans_record.approve_with_record = trans_matcher.find_similar(
            recent_pending, trans_record
        )
        yield trans_record


def get_notification_list(user):
    """Get recent transactions, resolutions and news posts, build human friendly
    messages for each, and sort them by created time.
    """
    now = datetime.datetime.now()
    days = 3

    transactions = db.get_transaction_notifications(user, days)
    resolutions = db.get_recent_resolutions(user, days)
    news_posts = models.NewsPost.objects.filter(
        time_created__gte=now - datetime.timedelta(days), site=config.SITE_ID
    )

    def build_transaction_message(trans):
        if trans.status == "pending":
            action = "created a"
        elif trans.status == "rejected":
            action = "rejected your"
        else:
            action = "confirmed your"
        return (
            "%s %s transaction for a %s of %s."
            % (
                trans.creator_person,
                action,
                trans.targets_transaction_type,
                trans.value_repr,
            ),
            trans.time_created,
        )

    def build_resolution_message(res):
        return (
            "Your balance with %s was resolved for %s."
            % (res.other_person, res.relative_value_repr),
            res.resolution.time_confirmed,
        )

    def build_news_post_message(post):
        return "%s posted '%s'." % (post.author, post.title), post.time_created

    return [
        i[0]
        for i in sorted(
            itertools.chain(
                (build_transaction_message(t) for t in transactions),
                (build_resolution_message(r) for r in resolutions),
                (build_news_post_message(n) for n in news_posts),
            ),
            key=itemgetter(1),
            reverse=True,
        )
    ]


@login_required
def home(request):
    """Setup homepage context."""
    context = {}

    # New Transaction form
    new_trans_form_data = request.POST if request.method == "POST" else None
    context["new_transaction_form"] = forms.TransactionRecordForm(
        web.form_data(request),
        initial={
            "currency": request.user.person.default_currency,
            "transaction_time": datetime.datetime.now().strftime("%x %X"),
        },
    )

    context["pending_trans_records"] = list(build_pending_trans_records(request))

    # Recent transactions, that may be confirmed
    context["recent_trans_records"] = db.get_recent_trans_for_user(request.user)

    # Currency balances
    context["balances"] = db.get_balances(request.user)

    # Notifications for recent news, transactions, balances
    context["notifications"] = get_notification_list(request.user)

    return web.render_context(request, "home.html", context=context)


@login_required
def settings(request):
    """Build context for settings page."""
    context = {
        "num_transactions": db.get_transaction_count(request.user),
        "num_balances": db.get_balances(request.user).count(),
    }

    # User account form
    context["user_form"] = forms.UserEditForm(
        web.form_data(request), instance=request.user
    )
    context["password_form"] = forms.PasswordChangeForm(web.form_data(request))

    # Person forms
    context["person_form"] = forms.PersonForm(
        web.form_data(request), instance=request.user.person
    )

    # Exchange rates
    context["exchange_rates"] = db.get_exchange_rates(request.user)
    context["exchange_rate_form"] = forms.ExchangeRateForm(web.form_data(request))
    return web.render_context(request, "settings.html", context=context)


@login_required
@require_POST
def exchange_rate_new(request):
    form = forms.ExchangeRateForm(request.POST)
    if form.is_valid():
        form.save(request.user)
        messages.success(request, "Exchange rate created.")
        return redirect("settings")
    return settings(request)


@login_required
@require_GET
def exchange_rate_delete(request, rate_id):
    exchange_rate = db.models.ExchangeRate.objects.get(
        id=rate_id, person=request.user.person
    )
    exchange_rate.delete()
    messages.success(request, "Exchange rate removed.")
    return redirect("settings")


@login_required
@require_POST
def person_update(request):
    """Update person details."""
    form = forms.PersonForm(request.POST, instance=request.user.person)
    if form.is_valid():
        form.save()
        messages.success(request, "Settings updated.")
        return redirect("settings")
    return settings(request)


@login_required
@require_POST
def user_update(request):
    form = forms.UserEditForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("settings")
    return settings(request)


@require_POST
def user_new(request):
    form = forms.UserCreateForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        user = models.User.objects.create_user(
            data["username"], data["email"], data["password"]
        )
        user.first_name = data["first_name"]
        user.last_name = data["last_name"]
        user.save()
        user = auth.authenticate(username=data["username"], password=data["password"])
        auth.login(request, user)
        return redirect("home")

    # TODO: error message
    return index(request)


@login_required
@require_POST
def transaction_new(request):
    """Create a new transaction record."""
    form = forms.TransactionRecordForm(request.POST)
    if form.is_valid():
        form.save(request.user)
        messages.success(request, "Transaction record saved.")
        return redirect("home")
    return home(request)


@require_GET
def transaction_list(request):
    """List transactions."""
    context = {}
    context["filter_form"] = filter_form = forms.TransferListForm(request.GET)
    filters = filter_form.cleaned_data if filter_form.is_valid() else {}

    context["records"] = db.get_transfer_history(request.user, filters)
    return web.render_context(request, "transaction_list.html", context=context)


@require_GET
def transaction_confirm(request, trans_record_id):
    """Confirm a transaction record from another person."""
    trans_record = db.get_trans_record_for_user(trans_record_id, request.user)
    db.confirm_trans_record(trans_record)
    messages.success(request, "Transaction confirmed.")
    return redirect("home")


@require_POST
def transaction_modify(request, trans_record_id):
    """Modify a transaction record from another person."""
    # TODO: load existing matching transaction
    form = forms.TransactionRecordForm(request.POST)
    if form.is_valid():
        form.save(request.user)
        messages.success(request, "Transaction modified.")
        return redirect("home")
    # TODO: handle errors better, so they don't display on the create form.
    return home(request)


@require_GET
def transaction_reject(request, trans_record_id):
    """Reject a transaction from another user."""
    db.reject_trans_record(trans_record_id, request.user)
    messages.success(request, "Transaction rejected.")
    return redirect("home")


def content_view(request, name):
    """Get a piece of content by name."""
    content = models.Content.objects.get(name=name, site=config.SITE_ID)
    return web.render_context(request, "content.html", context={"content": content})


def news(request):
    """Get latest news posts."""
    news = models.NewsPost.objects.filter(
        site=config.SITE_ID,
    ).order_by(
        "-time_created"
    )[:20]
    content = models.Content.objects.get(name="news_header", site=config.SITE_ID)

    context = {"news_posts": news, "header": content}
    return web.render_context(request, "news.html", context=context)


def export_data(request):
    """Export all data for a user."""
    data = {
        "balances": [
            balance.export_data() for balance in db.get_balances(request.user)
        ],
        "transfers": [
            transfer.export_data()
            for transfer in db.get_transfer_history(request.user, {})
        ],
        "exchange_rates": [
            rate.export_data() for rate in db.get_exchange_rates(request.user)
        ],
    }
    return HttpResponse(json.dumps(data), mimetype="application/json")
