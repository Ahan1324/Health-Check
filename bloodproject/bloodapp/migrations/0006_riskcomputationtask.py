from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('bloodapp', '0005_healthcondition_expert_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='RiskComputationTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('condition_id', models.CharField(max_length=150)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('done', 'Done'), ('error', 'Error')], default='queued', max_length=10)),
                ('result', models.JSONField(blank=True, null=True)),
                ('error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='riskcomputationtask',
            index=models.Index(fields=['user', 'condition_id', 'status'], name='bloodapp_ri_user_id_7d74aa_idx'),
        ),
    ]


