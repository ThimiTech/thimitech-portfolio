from django.db import models


class TeamMember(models.Model):
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    initials = models.CharField(max_length=10)
    image = models.ImageField(upload_to='team/', blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class SocialMedia(models.Model):
    team_member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name='social_media'
    )

    platform = models.CharField(
        max_length=50,
        choices=[
            ('linkedin', 'LinkedIn'),
            ('github', 'GitHub'),
            ('instagram', 'Instagram'),
            ('facebook', 'Facebook'),
            ('twitter', 'X (Twitter)'),
        ]
    )

    url = models.URLField()

    def __str__(self):
        return f"{self.team_member.name} - {self.platform}"