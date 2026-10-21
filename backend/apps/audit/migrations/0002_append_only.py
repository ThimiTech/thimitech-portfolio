from django.db import migrations


def install_guard(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("""
            CREATE FUNCTION audit_prevent_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Audit records are append-only';
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER audit_log_append_only
            BEFORE UPDATE OR DELETE ON audit_auditlog
            FOR EACH ROW EXECUTE FUNCTION audit_prevent_mutation();
        """)


def remove_guard(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('DROP TRIGGER IF EXISTS audit_log_append_only ON audit_auditlog; DROP FUNCTION IF EXISTS audit_prevent_mutation();')


class Migration(migrations.Migration):
    dependencies = [('audit', '0001_initial')]
    operations = [migrations.RunPython(install_guard, remove_guard)]
