# Generated by Django 5.2.2 on 2025-06-10 18:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asignacion_turnos', '0005_alter_sucesion_usuario_carga_horario'),
    ]

    operations = [
        migrations.AddField(
            model_name='sucesion',
            name='horario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='asignacion_turnos.horario'),
        ),
    ]
