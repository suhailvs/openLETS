## OpenLETS

openLETS is an open source local exchange trading system 


### Installation

```
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata sample
python manage.py runserver
python manage.py shell < core/resolve_balances.py
```

