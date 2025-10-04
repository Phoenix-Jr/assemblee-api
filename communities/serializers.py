from rest_framework import serializers
from .models import (
    Community, Pastor, Service, Ministry, Event, 
    BibleStudy, Meditation, Testimony, Gallery, Member
)

class ServiceSerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    
    class Meta:
        model = Service
        fields = ['id', 'day', 'day_display', 'time', 'type', 'description']


class PastorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Pastor
        fields = [
            'id', 'full_name', 'title', 'bio', 
            'experience_years', 'image', 'image_url',
            'phone', 'email', 'is_principal'
        ]


class MinistrySerializer(serializers.ModelSerializer):
    leader_name = serializers.CharField(source='leader.__str__', read_only=True)
    activities = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Ministry
        fields = [
            'id', 'name', 'description', 'leader_name',
            'participants_count', 'meeting_time', 'activities'
        ]


class EventSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'date', 'start_time', 'end_time',
            'type', 'type_display', 'description', 'location',
            'organizer', 'registration_required', 'max_participants'
        ]


class CommunityListSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    country_name = serializers.CharField(source='city.country.name', read_only=True)
    
    class Meta:
        model = Community
        fields = [
            'id', 'slug', 'name', 'full_name', 'founded_year',
            'slogan', 'members_count', 'city_name', 'country_name',
            'is_active'
        ]


class CommunityDetailSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    pastors = PastorSerializer(many=True, read_only=True)
    ministries = MinistrySerializer(many=True, read_only=True)
    upcoming_events = serializers.SerializerMethodField()
    
    class Meta:
        model = Community
        fields = [
            'id', 'slug', 'name', 'full_name', 'founded_year', 'slogan',
            'description', 'vision', 'address', 'city', 'latitude', 'longitude',
            'phone', 'email', 'website', 'members_count', 'leaders_count',
            'weekly_services_count', 'baptisms_current_year', 'is_active',
            'services', 'pastors', 'ministries', 'upcoming_events'
        ]
    
    def get_upcoming_events(self, obj):
        from datetime import date
        events = obj.events.filter(date__gte=date.today()).order_by('date')[:5]
        return EventSerializer(events, many=True).data


class MeditationSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.__str__', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Meditation
        fields = [
            'id', 'title', 'author_name', 'bible_verse', 'type',
            'type_display', 'category', 'category_display', 'content',
            'duration_minutes', 'published_date'
        ]


class TestimonySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Testimony
        fields = [
            'id', 'author_name', 'title', 'category', 'category_display',
            'excerpt', 'full_content', 'date'
        ]


class MemberSerializer(serializers.ModelSerializer):
    community_name = serializers.CharField(source='community.name', read_only=True)
    
    class Meta:
        model = Member
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'community_name', 'join_date', 'is_active'
        ]
        extra_kwargs = {
            'email': {'write_only': True},
            'phone': {'write_only': True}
        }
