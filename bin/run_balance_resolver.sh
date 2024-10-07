export DJANGO_SETTINGS_MODULE=mysite.settings
export PYTHONPATH=.
python core/jobs/resolve_balances.py $@
