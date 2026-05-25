from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authorship', '0003_demo_pipeline_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='tblattributionexperiment',
            name='started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tblattributionexperiment',
            name='finished_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tblattributionexperiment',
            name='error_message',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='tblattributionexperiment',
            name='build_status',
            field=models.CharField(default='pending', max_length=100),
        ),
    ]
