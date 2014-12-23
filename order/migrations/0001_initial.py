# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bundle',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('start', models.DateTimeField(auto_now_add=True)),
                ('open', models.BooleanField(default=True)),
            ],
            options={
                'get_latest_by': 'start',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('enclosure', models.BooleanField(verbose_name='Einlage bezahlt', default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('amount', models.PositiveIntegerField(blank=True, default=0)),
                ('delivered', models.PositiveIntegerField(blank=True, null=True)),
                ('bundle', models.ForeignKey(to='order.Bundle', related_name='orders')),
                ('group', models.ForeignKey(to='order.Group')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('price', models.DecimalField(verbose_name='Preis', decimal_places=2, max_digits=10)),
                ('available', models.BooleanField(verbose_name='Verfügbar', default=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('order_name', models.CharField(blank=True, max_length=255)),
                ('divisor', models.PositiveIntegerField(default=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='product',
            name='unit',
            field=models.ForeignKey(verbose_name='Einheit', to='order.Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='product',
            field=models.ForeignKey(to='order.Product'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='order',
            unique_together=set([('group', 'product', 'bundle')]),
        ),
    ]
