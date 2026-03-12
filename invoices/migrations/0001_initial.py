from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_name', models.CharField(max_length=255)),
                ('file', models.FileField(upload_to='invoices/')),
                ('vendor_name', models.CharField(blank=True, max_length=255)),
                ('invoice_number', models.CharField(blank=True, max_length=120)),
                ('invoice_date', models.DateField(blank=True, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('currency', models.CharField(blank=True, max_length=12)),
                ('total_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('tax_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('invoice_type', models.CharField(blank=True, max_length=120)),
                ('extracted_data', models.JSONField(blank=True, default=dict)),
                ('erp_payload', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('uploaded', 'Uploaded'), ('processed', 'Processed'), ('erp_synced', 'ERP Synced'), ('failed', 'Failed')], default='uploaded', max_length=20)),
                ('processing_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
