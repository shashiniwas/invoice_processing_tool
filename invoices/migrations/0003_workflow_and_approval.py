from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0002_invoice_uploaded_by'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('show_vendor_name', models.BooleanField(default=True)),
                ('show_invoice_number', models.BooleanField(default=True)),
                ('show_invoice_date', models.BooleanField(default=True)),
                ('show_due_date', models.BooleanField(default=True)),
                ('show_currency', models.BooleanField(default=True)),
                ('show_total_amount', models.BooleanField(default=True)),
                ('show_tax_amount', models.BooleanField(default=True)),
                ('show_invoice_type', models.BooleanField(default=True)),
                ('show_table_data', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ApprovalAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.PositiveIntegerField(default=0)),
                ('action', models.CharField(choices=[('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')], max_length=20)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='WorkflowStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.PositiveIntegerField()),
                ('approver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_steps', to=settings.AUTH_USER_MODEL)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='invoices.workflow')),
            ],
            options={'ordering': ['level'], 'unique_together': {('workflow', 'level')}},
        ),
        migrations.AddField(
            model_name='invoice',
            name='approval_state',
            field=models.CharField(choices=[('draft', 'Draft'), ('in_approval', 'In Approval'), ('rejected', 'Rejected'), ('final_approved', 'Final Approved')], default='draft', max_length=20),
        ),
        migrations.AddField(
            model_name='invoice',
            name='current_approval_level',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='invoice',
            name='workflow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='invoices.workflow'),
        ),
        migrations.AddField(
            model_name='approvalaction',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_actions', to='invoices.invoice'),
        ),
        migrations.AddField(
            model_name='usernotification',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='invoices.invoice'),
        ),
        migrations.AddField(
            model_name='usernotification',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoice_notifications', to=settings.AUTH_USER_MODEL),
        ),
    ]
