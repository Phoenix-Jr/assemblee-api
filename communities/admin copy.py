# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    Country, City, Community, Pastor, Service, Ministry, MinistryActivity,
    Event, BibleStudy, ReadingProgram, Meditation, Leader, LeaderSpecialty,
    Baptism, BaptismRequirement, BaptismStatistics, Testimony, Gallery,
    GalleryImage, Member, MemberMinistryParticipation, EventRegistration
)

# Inlines
class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    fields = ['day', 'time', 'type', 'description']


class MinistryActivityInline(admin.TabularInline):
    model = MinistryActivity
    extra = 1
    fields = ['name', 'description', 'order']


class LeaderSpecialtyInline(admin.TabularInline):
    model = LeaderSpecialty
    extra = 1


class BaptismRequirementInline(admin.TabularInline):
    model = BaptismRequirement
    extra = 1
    fields = ['requirement', 'order']


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 1
    fields = ['image', 'image_url', 'caption', 'order']


# Admin Classes
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'country']
    list_filter = ['country']
    search_fields = ['name', 'country__name']
    ordering = ['country', 'name']


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'name', 'city', 'founded_year', 'members_count', 'is_active']
    list_filter = ['is_active', 'city__country', 'city', 'founded_year']
    search_fields = ['name', 'full_name', 'slogan', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ServiceInline, BaptismRequirementInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('slug', 'name', 'full_name', 'founded_year', 'slogan', 'is_active')
        }),
        ('Description', {
            'fields': ('description', 'vision')
        }),
        ('Localisation', {
            'fields': ('address', 'city', 'latitude', 'longitude')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Statistiques', {
            'fields': ('members_count', 'leaders_count', 'weekly_services_count', 'baptisms_current_year')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Pastor)
class PastorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'title', 'community', 'is_principal', 'experience_years']
    list_filter = ['is_principal', 'community', 'experience_years']
    search_fields = ['first_name', 'last_name', 'title', 'bio']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'title', 'is_principal')
        }),
        ('Contact', {
            'fields': ('phone', 'email')
        }),
        ('Profil', {
            'fields': ('bio', 'experience_years', 'image', 'image_url')
        }),
        ('Affectation', {
            'fields': ('community',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ['name', 'community', 'leader', 'participants_count', 'meeting_time']
    list_filter = ['community']
    search_fields = ['name', 'description']
    inlines = [MinistryActivityInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'community', 'date', 'start_time', 'type', 'organizer']
    list_filter = ['type', 'community', 'date', 'is_recurring']
    search_fields = ['title', 'description', 'organizer']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('community', 'title', 'type', 'description')
        }),
        ('Date et lieu', {
            'fields': ('date', 'start_time', 'end_time', 'location')
        }),
        ('Organisation', {
            'fields': ('organizer', 'is_recurring', 'registration_required', 'max_participants')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(BibleStudy)
class BibleStudyAdmin(admin.ModelAdmin):
    list_display = ['title', 'community', 'teacher', 'start_date', 'duration_weeks', 'is_active']
    list_filter = ['is_active', 'community', 'start_date']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReadingProgram)
class ReadingProgramAdmin(admin.ModelAdmin):
    list_display = ['title', 'community', 'current_book', 'progress_percentage', 'participants_count', 'is_active']
    list_filter = ['is_active', 'community']
    search_fields = ['title', 'current_book', 'weekly_reading']
    readonly_fields = ['created_at', 'updated_at']
    
    def progress_percentage(self, obj):
        color = 'green' if obj.progress_percentage >= 75 else 'orange' if obj.progress_percentage >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color,
            obj.progress_percentage
        )
    progress_percentage.short_description = 'Progression'


@admin.register(Meditation)
class MeditationAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'community', 'type', 'category', 'published_date', 'is_published']
    list_filter = ['is_published', 'type', 'category', 'community', 'published_date']
    search_fields = ['title', 'content', 'bible_verse']
    date_hierarchy = 'published_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Leader)
class LeaderAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'position', 'community', 'experience_years', 'is_active']
    list_filter = ['is_active', 'community', 'experience_years']
    search_fields = ['first_name', 'last_name', 'position']
    inlines = [LeaderSpecialtyInline]
    readonly_fields = ['created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Nom complet'


@admin.register(Baptism)
class BaptismAdmin(admin.ModelAdmin):
    list_display = ['community', 'date', 'time', 'candidates_count', 'coordinator', 'is_completed']
    list_filter = ['is_completed', 'community', 'date']
    date_hierarchy = 'date'
    search_fields = ['location']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BaptismStatistics)
class BaptismStatisticsAdmin(admin.ModelAdmin):
    list_display = ['community', 'year', 'count']
    list_filter = ['community', 'year']
    ordering = ['-year', 'community']


@admin.register(Testimony)
class TestimonyAdmin(admin.ModelAdmin):
    list_display = ['title', 'author_name', 'community', 'category', 'date', 'is_published', 'is_verified']
    list_filter = ['is_published', 'is_verified', 'category', 'community', 'date']
    search_fields = ['title', 'author_name', 'excerpt', 'full_content']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['publish_testimonies', 'verify_testimonies']
    
    def publish_testimonies(self, request, queryset):
        queryset.update(is_published=True)
        self.message_user(request, f"{queryset.count()} témoignage(s) publié(s).")
    publish_testimonies.short_description = "Publier les témoignages sélectionnés"
    
    def verify_testimonies(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} témoignage(s) vérifié(s).")
    verify_testimonies.short_description = "Vérifier les témoignages sélectionnés"


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ['title', 'community', 'images_count', 'event', 'is_public', 'created_at']
    list_filter = ['is_public', 'community', 'created_at']
    search_fields = ['title', 'description']
    inlines = [GalleryImageInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'email', 'community', 'join_date', 'is_active']
    list_filter = ['is_active', 'community', 'join_date']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    date_hierarchy = 'join_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'first_name', 'last_name', 'date_of_birth')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Affiliation', {
            'fields': ('community', 'baptism', 'join_date', 'is_active')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Nom complet'


@admin.register(MemberMinistryParticipation)
class MemberMinistryParticipationAdmin(admin.ModelAdmin):
    list_display = ['member', 'ministry', 'role', 'join_date', 'is_active']
    list_filter = ['is_active', 'ministry__community', 'ministry']
    search_fields = ['member__first_name', 'member__last_name', 'role']
    date_hierarchy = 'join_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['event', 'member', 'registration_date', 'attended']
    list_filter = ['attended', 'event__community', 'registration_date']
    search_fields = ['event__title', 'member__first_name', 'member__last_name']
    date_hierarchy = 'registration_date'
    readonly_fields = ['registration_date', 'created_at', 'updated_at']
    
    actions = ['mark_as_attended']
    
    def mark_as_attended(self, request, queryset):
        queryset.update(attended=True)
        self.message_user(request, f"{queryset.count()} inscription(s) marquée(s) comme présente(s).")
    mark_as_attended.short_description = "Marquer comme présent"