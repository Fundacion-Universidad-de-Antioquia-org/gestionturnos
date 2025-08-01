# Generated by Django 5.2.2 on 2025-06-16 19:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asignacion_turnos', '0014_remove_sucesion_cargo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cambios_de_turnos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_solicitante', models.CharField(max_length=10)),
                ('nombre_solicitante', models.CharField(max_length=100)),
                ('turno_solicitante', models.TextField()),
                ('codigo_receptor', models.CharField(max_length=10)),
                ('nombre_receptor', models.CharField(max_length=100)),
                ('turno_receptor', models.TextField()),
                ('estado_cambio_emp', models.CharField(default='Pendiente', max_length=30)),
                ('fecha', models.DateField()),
            ],
        ),
    ]
