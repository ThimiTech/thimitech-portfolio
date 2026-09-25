from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': False},
        }

    def create(self, validated_data):
        username = validated_data.get('username')

        if not username:
            username = validated_data['email'].split('@')[0]

        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password']
        )

        return user