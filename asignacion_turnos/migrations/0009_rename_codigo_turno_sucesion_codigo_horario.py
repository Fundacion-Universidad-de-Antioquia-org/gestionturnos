# Generated by Django 5.2.2 on 2025-06-10 20:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('asignacion_turnos', '0008_sucesion_codigo_turno_alter_horario_turno'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sucesion',
            old_name='codigo_turno',
            new_name='codigo_horario',
        ),
    ]
