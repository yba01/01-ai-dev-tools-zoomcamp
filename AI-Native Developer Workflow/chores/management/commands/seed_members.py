from django.core.management.base import BaseCommand

from chores.models import Member


class Command(BaseCommand):
    help = "Create the sample household members if they do not already exist."

    def handle(self, *args, **options):
        names = ("Alex", "Jordan", "Sam")
        created_count = 0

        for name in names:
            _, created = Member.objects.get_or_create(name=name)
            created_count += created

        self.stdout.write(
            self.style.SUCCESS(
                f"Sample household ready; created {created_count} member(s)."
            )
        )