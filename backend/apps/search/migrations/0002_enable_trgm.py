from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):
    dependencies = [
        ("search", "0001_initial"),
        ("catalogue", "0001_initial"),
        ("parties", "0001_initial"),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunSQL(
            sql=[
                "CREATE INDEX IF NOT EXISTS item_name_trgm "
                "ON catalogue_item USING gin (name gin_trgm_ops);",
                "CREATE INDEX IF NOT EXISTS party_name_trgm "
                "ON parties_party USING gin (name gin_trgm_ops);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS item_name_trgm;",
                "DROP INDEX IF EXISTS party_name_trgm;",
            ],
        ),
    ]
