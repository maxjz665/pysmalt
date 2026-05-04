from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authorship', '0002_alter_tblattributionexperiment_detailed_results_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tblsyntacticfeature',
            name='vector',
            field=models.JSONField(blank=True, default=list, help_text='193-component feature vector used by the authorship pipeline'),
        ),
        migrations.AddField(
            model_name='tblsyntacticfeature',
            name='vector_size',
            field=models.IntegerField(default=193, help_text='Feature vector size, expected to be 193'),
        ),
        migrations.AddField(
            model_name='tblsyntacticfeature',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tblauthorprofile',
            name='method',
            field=models.CharField(default='profile', max_length=20),
        ),
        migrations.AddField(
            model_name='tblauthorprofile',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tblattributionexperiment',
            name='metric',
            field=models.CharField(default='', help_text='Primary metric used by this experiment', max_length=50),
        ),
        migrations.AddField(
            model_name='tblattributionexperiment',
            name='metrics',
            field=models.JSONField(default=dict, help_text='Metrics dict: accuracy, macro_precision, macro_recall, macro_f1'),
        ),
    ]
