# Generated by Django 5.1.1 on 2024-10-07 00:41

import core.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('decimal_places', models.IntegerField(default=0)),
                ('default', models.BooleanField(default=False)),
                ('time_created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_confirmed', models.DateTimeField(auto_now_add=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Balance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(default=0)),
                ('time_updated', models.DateTimeField(auto_now=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.currency')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('default_currency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.currency')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PersonBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credited', models.BooleanField()),
                ('balance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.balance')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.person')),
            ],
        ),
        migrations.AddField(
            model_name='balance',
            name='persons',
            field=models.ManyToManyField(blank=True, related_name='balances', through='core.PersonBalance', to='core.person'),
        ),
        migrations.CreateModel(
            name='PersonResolution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credited', models.BooleanField()),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.person')),
            ],
        ),
        migrations.CreateModel(
            name='Resolution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(default=0)),
                ('time_confirmed', models.DateTimeField(auto_now_add=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.currency')),
                ('persons', models.ManyToManyField(blank=True, related_name='resolutions', through='core.PersonResolution', to='core.person')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='personresolution',
            name='resolution',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.resolution'),
        ),
        migrations.CreateModel(
            name='TransactionRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(default=0)),
                ('from_receiver', models.BooleanField()),
                ('rejected', models.BooleanField(default=False)),
                ('transaction_time', models.DateTimeField()),
                ('time_created', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('creator_person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_records_creator', to='core.person')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.currency')),
                ('target_person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_records_target', to='core.person')),
                ('transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transaction_records', to='core.transaction')),
            ],
            options={
                'abstract': False,
            },
            bases=(core.models.DictableModel, models.Model),
        ),
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_rate', models.IntegerField()),
                ('dest_rate', models.IntegerField()),
                ('time_created', models.DateTimeField(auto_now_add=True)),
                ('dest_currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.currency')),
                ('source_currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.currency')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.person')),
            ],
            options={
                'unique_together': {('person', 'source_currency', 'dest_currency')},
            },
        ),
    ]
