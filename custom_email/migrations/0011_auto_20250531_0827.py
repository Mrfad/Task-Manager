from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('custom_email', '0010_email_uid'),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunSQL(
            sql="""
                CREATE INDEX email_search_vector_idx ON custom_email_email
                USING GIN (
                    to_tsvector('english',
                        left(subject, 1000) || ' ' ||
                        left(sender, 1000) || ' ' ||
                        left(body, 5000)
                    )
                );
            """,
            reverse_sql="DROP INDEX IF EXISTS email_search_vector_idx;"
        ),
    ]